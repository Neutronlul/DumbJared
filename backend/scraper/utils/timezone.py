from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from django.conf import settings
from geopy.geocoders import Nominatim
from tzfpy import get_tz

if TYPE_CHECKING:
    from geopy.location import Location

    from scraper.models import GeocodedAddress


def geocode_address(address: str) -> GeocodedAddress:
    """Geocode a postal address and return cached or newly created GeocodedAddress.

    Geocodes the provided address using Nominatim, determines its timezone using tzfpy,
    and stores the result in the database. Subsequent calls with the same address are
    returned from cache.

    Args:
        address: A postal address string to geocode.

    Returns:
        GeocodedAddress: A model instance with the geocoded coordinates and timezone.

    Raises:
        ValueError: If the address is empty, cannot be geocoded by Nominatim, or the
            timezone cannot be determined for the geocoded location.

    """
    from scraper.models import GeocodedAddress  # noqa: PLC0415 to avoid circular import

    address = address.strip()

    if not address:
        msg = "Address cannot be empty"
        raise ValueError(msg)

    if cache_entry := GeocodedAddress.objects.filter(address=address).first():
        return cache_entry

    location: Location | None = Nominatim(
        timeout=10,
        user_agent=settings.NOMINATIM_USER_AGENT,
    ).geocode(
        address,
    )

    if location is None:
        msg = f"Could not geocode address: {address}"
        raise ValueError(msg)

    timezone = get_tz(location.longitude, location.latitude)

    if not timezone:
        msg = (
            f"Could not determine timezone for location: {location.address} "
            f"({location.latitude}, {location.longitude})"
        )
        raise ValueError(msg)

    timezone = ZoneInfo(timezone)

    geocoded_address, _ = (
        GeocodedAddress.objects.get_or_create(  # To guard against race conditions
            address=address,
            defaults={
                "timezone": timezone,
                "longitude": location.longitude,
                "latitude": location.latitude,
            },
        )
    )

    return geocoded_address
