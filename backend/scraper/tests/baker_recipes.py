import jwt as pyjwt
from faker import Faker
from model_bakery.recipe import Recipe

from scraper.models import GeocodedAddress, ScraperAccount

fake = Faker()


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
    address=lambda: fake.address().replace("\n", ", "),
    longitude=fake.longitude,
    latitude=fake.latitude,
)
