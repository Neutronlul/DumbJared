from urllib.parse import urlparse

from api.models import Venue


def get_base_url() -> str:
    """Return a single canonical hostname for scraping.

    Inspects Venue.url values in the database, normalizes hostnames by
    removing a leading "www.", and returns the unique hostname.

    Raises ValueError if no venues exist or if more than one distinct
    normalized hostname is found.
    """
    urls = Venue.objects.values_list("url", flat=True)
    if not urls:
        msg = "No venues found in database; cannot determine base URL"
        raise ValueError(msg)

    hostnames = {
        urlparse(url).hostname.removeprefix("www.")
        for url in urls
        if urlparse(url).hostname is not None
    }

    if len(hostnames) != 1:
        msg = (
            f"Multiple distinct venue hostnames found in database: "
            f"{hostnames}; cannot determine base URL"
        )
        raise ValueError(msg)

    return next(iter(hostnames))
