import jwt as pyjwt
from model_bakery.recipe import Recipe

from scraper.models import GeocodedAddress, ScraperAccount

player_id = "69d49757f4205d88e104a910"
scraper_account = Recipe(
    ScraperAccount,
    name="Test Account",
    email="test@example.com",
    token=pyjwt.encode(
        {"playerid": player_id, "email": "test@example.com"},
        "secret" * 6,  # HS256 length requirement
        algorithm="HS256",
    ),
    player_id=player_id,
)
geocoded_address = Recipe(
    GeocodedAddress,
    address="1640 Riverside Drive, Hill Valley CA 94952",
    timezone="America/Los_Angeles",
    longitude=-122.631389,
    latitude=38.245833,
)
