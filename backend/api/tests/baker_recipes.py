from model_bakery.recipe import Recipe
from model_bakery.utils import seq

from api.models import Event, Quizmaster, Team

quizmaster = Recipe(Quizmaster, name="John Doe")

team = Recipe(Team, team_id=seq(0))

event = Recipe(Event)
