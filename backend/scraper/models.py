from django.core.validators import RegexValidator
from django.db import models

from api.models import (
    EVENT_SLUG_REGEX as PLAYER_ID_REGEX,  # Jank, should be centralized
)
from core.models import TimeStampedModel


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

    class Meta:
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
