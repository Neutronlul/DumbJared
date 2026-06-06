from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from timezone_field import TimeZoneField

from core.constants import HEX_24_REGEX as PLAYER_ID_REGEX
from core.models import TimeStampedModel
from core.validators import validate_not_empty_string
from scraper.utils.timezone import geocode_address


class ScraperAccount(TimeStampedModel):
    name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Username. Can be blank, probably shouldn't be.",
    )
    email = models.EmailField(
        unique=True,
        help_text="Must be routed to the email worker to receive login codes",
    )

    token = models.CharField(
        max_length=1000,
        blank=True,
        default="",
        help_text="JWT issued after login",
    )
    player_id = models.CharField(
        max_length=24,
        blank=True,
        validators=[
            RegexValidator(
                regex=PLAYER_ID_REGEX,
                message="Player ID must be exactly 24 lowercase hex characters",
            ),
        ],
        default="",
        help_text="Player ID (exactly 24 lowercase hexadecimal characters)",
        verbose_name="Player ID",
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=models.Q(player_id__regex=PLAYER_ID_REGEX)
                | models.Q(player_id=""),
                name="player_id_twenty_four_hex",
            ),
        )
        ordering = ("email",)

    def __str__(self) -> str:
        return self.name or self.email


class GeocodedAddress(TimeStampedModel):
    address = models.CharField(
        max_length=500,
        unique=True,
        help_text="The postal address that was geocoded",
        validators=[validate_not_empty_string],
    )
    timezone = TimeZoneField(
        verbose_name="Time Zone",
        help_text="The timezone corresponding to the geocoded address",
        validators=[validate_not_empty_string],
    )

    longitude = models.FloatField(
        help_text="The longitude of the geocoded address",
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180),
        ],
    )
    latitude = models.FloatField(
        help_text="The latitude of the geocoded address",
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90),
        ],
    )

    class Meta(TimeStampedModel.Meta):
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(address=""),
                name="address_not_empty",
            ),
            models.CheckConstraint(
                condition=~models.Q(timezone=""),
                name="timezone_not_empty",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180) & models.Q(longitude__lte=180),
                name="valid_longitude",
            ),
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90) & models.Q(latitude__lte=90),
                name="valid_latitude",
            ),
        )
        ordering = ("address",)
        verbose_name_plural = "geocoded addresses"

    def __str__(self) -> str:
        return f"{self.address} ({self.timezone})"

    @classmethod
    def create_from_address(cls, address: str) -> GeocodedAddress:
        return geocode_address(address)
