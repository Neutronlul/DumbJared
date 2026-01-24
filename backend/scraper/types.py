from dataclasses import dataclass
from datetime import date, time


@dataclass
class GameData:
    type: str
    day: int
    time: time

    def __post_init__(self):
        if not (0 <= self.day <= 6):
            raise ValueError("day must be an integer between 0 (Monday) and 6 (Sunday)")


@dataclass
class VenueData:
    name: str
    games: list[GameData]


@dataclass
class TeamData:
    team_id: int | None
    name: str
    score: int

    def __post_init__(self):
        if self.team_id is not None and self.team_id < 0:
            raise ValueError("team_id must be a non-negative integer or None")
        if not (-1 <= self.score <= 112):
            raise ValueError("score must be between -1 and 112 inclusive")


@dataclass
class EventData:
    date: date
    game_type: str
    quizmaster: str
    description: str | None
    teams: list[TeamData]


@dataclass
class PageData:
    venue_data: VenueData
    event_data: list[EventData]
