from calendar import MONDAY, SUNDAY
from dataclasses import dataclass
from typing import TYPE_CHECKING
from core.constants import MAX_TEAM_SCORE, MIN_TEAM_SCORE

if TYPE_CHECKING:
    from datetime import date, time


@dataclass
class GameData:
    type: str
    day: int
    time: time

    def __post_init__(self) -> None:
        if not (MONDAY <= self.day <= SUNDAY):
            msg = "day must be an integer between 0 (Monday) and 6 (Sunday)"
            raise ValueError(msg)


@dataclass
class VenueData:
    name: str
    address: str
    games: list[GameData]


@dataclass
class TeamData:
    team_id: int | None
    name: str
    score: int

    def __post_init__(self) -> None:
        if self.team_id is not None and self.team_id < 0:
            msg = "team_id must be a non-negative integer or None"
            raise ValueError(msg)
        if not (MIN_TEAM_SCORE <= self.score <= MAX_TEAM_SCORE):
            msg = (
                f"score must be between {MIN_TEAM_SCORE} and {MAX_TEAM_SCORE} inclusive"
            )
            raise ValueError(msg)


@dataclass
class EventData:
    date: date
    game_type: str
    quizmaster: str
    description: str
    teams: list[TeamData]


@dataclass
class PageData:
    venue_data: VenueData
    event_data: list[EventData]
