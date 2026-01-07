from api.models import Quizmaster, Team

from model_bakery.recipe import Recipe
from model_bakery.utils import seq


quizmaster = Recipe(Quizmaster, name="John Doe")

team = Recipe(Team, team_id=seq(0))
