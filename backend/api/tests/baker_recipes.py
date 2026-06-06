from model_bakery.recipe import Recipe, foreign_key
from model_bakery.utils import seq

from api.models import Event, Game, Quizmaster, Team, Venue
from scraper.tests.baker_recipes import geocoded_address

quizmaster = Recipe(Quizmaster, name="John Doe")

team = Recipe(Team, team_id=seq(0))

venue = Recipe(Venue, address=foreign_key(geocoded_address))

game = Recipe(Game, venue=foreign_key(venue))

event = Recipe(Event, game=foreign_key(game))
