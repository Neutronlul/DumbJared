from api.models import (
    Event,
    Game,
    GameType,
    Quizmaster,
    Team,
    TeamEventParticipation,
    TeamName,
    Venue,
)
from datetime import date
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from functools import lru_cache
from scraper.types import PageData, EventData
from scraper.utils import sync_tasks
from scraper.utils.trivia_scraper import TriviaScraper
import logging


logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self, is_manual: bool = True):
        self.is_manual = is_manual

    def scrape_data(self, source_url: str, end_date: str | date | None) -> PageData:
        self.source_url = source_url
        self.end_date = end_date

        scraper = TriviaScraper(
            base_url=self.source_url, break_flag=self._process_end_date()
        )

        try:
            scraped_data = scraper.scrape()
            return scraped_data
        except Exception as e:
            logger.error(f"Error scraping data: {e}")
            raise

    def push_to_db(
        self, data: PageData, autoscrape_game_id: int | None = None
    ) -> None | bool:
        """
        Docstring for push_to_db

        :param self: Description
        :param data: Description
        :type data: PageData
        :param autoscrape_game_id: Description
        :type autoscrape_game_id: int | None
        :return: Only returns bools when self.is_manual is False.
        :rtype: bool | None
        """
        self.updated_event_pk = None
        self.updated_event_data = None

        if not data.event_data and not self.is_manual:
            return False

        with transaction.atomic():
            self.venue = self._create_or_update_venue(venue_name=data.venue_data.name)

            game_types = self._process_game_types(data=data)

            self.games = self._process_games(data=data, game_types=game_types)

            sync_tasks.sync(
                [game for (_type, day), game in self.games.items() if day is not None]
            )

            quizmasters = self._process_quizmasters(event_data=data.event_data)

            events_not_updated = self._process_autoscrape_event(
                event_data=data.event_data,
                autoscrape_game_id=autoscrape_game_id,
                quizmasters=quizmasters,
            )

            events = self._process_events(
                event_data=data.event_data,
                events_not_updated=events_not_updated,
                quizmasters=quizmasters,
            )

            teams = self._process_official_teams(event_data=data.event_data)

            guest_teams = self._process_guest_teams(event_data=data.event_data)

            self._process_autoscrape_teps()

            self._process_team_event_participations(
                event_data=data.event_data,
                events=events,
                teams=teams,
                guest_teams=guest_teams,
            )

        return True

    def _process_end_date(self) -> date | None:
        # In order of priority:
        # 1. If the end_date is already a date object, use it
        # 2. If it's a string, attempt to parse it
        #    (format: YYYY-MM-DD)
        # 3. Use the last event's date from the database for the provided venue url if available
        # 4. Default to None if no other date is available
        if isinstance(self.end_date, date):
            return self.end_date
        elif self.end_date is not None and isinstance(self.end_date, str):
            try:
                return date.fromisoformat(self.end_date)
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD.")
        elif self.end_date is None:
            try:
                return (
                    Event.objects.filter(game__venue__url=self.source_url)
                    .values_list("date", flat=True)
                    .latest("date")
                )
            except Event.DoesNotExist:
                return None
        else:
            raise ValueError("end_date must be a date object, string, or None.")

    @lru_cache
    def _match_game_to_event(self, game_type: str, day: int) -> Game:
        """
        Match an event to its corresponding game at the venue.

        Attempts to find a matching game based on game type and day of the week.
        Falls back to custom/unofficial games (day=None) if no official match found.

        Note: This method is cached using lru_cache.

        Args:
            game_type: The name of the game instance.
            day: The day of the week as an integer (0=Monday, 6=Sunday).

        Returns:
            The matched Game object.

        Raises:
            KeyError: If no matching game is found for the given game_type.
        """
        logger.debug(f"Matching game for type '{game_type}' on day {day}")
        # Attempt to match the event's game type to one of the provided games
        #
        # In order of priority:
        # 1. If there's an exact match at the venue for the event's
        #    game type and day, use that
        if game := self.games.get((game_type, day)):
            logger.debug(
                f"Found exact match for official game type '{game_type}' on day {day}"
            )
            return game

        # 2. If it's possible to match a custom game, do that
        elif game := self.games.get((game_type, None)):
            logger.debug(
                f"Falling back to custom game match for game type '{game_type}'"
            )
            return game

        # 3. If no games match, raise
        else:
            raise KeyError(
                f"No matching game found for type '{game_type}' on day {day}."
                f"Expected this game to exist in self.games."
            )

    def _create_or_update_venue(self, venue_name: str) -> Venue:
        """
        Add the venue name and url if not already in db
        If the name has changed, update it
        This enables hiding of the name field in
        the admin panel when adding a new venue

        Also update last_scraped_at field to current time
        """
        venue_obj, created = Venue.objects.get_or_create(
            url=self.source_url,
            defaults={"name": venue_name},
        )

        if not created and venue_obj.name != venue_name:
            venue_name_old = venue_obj.name
            venue_obj.name = venue_name
            venue_obj.save(update_fields=["name"])
            logger.info(
                f"Updated venue name from '{venue_name_old}' to '{venue_name}' for URL: {self.source_url}"
            )
        elif created:
            logger.info(f"Created new venue '{venue_name}' with URL: {self.source_url}")
        else:
            logger.debug(
                f"Venue '{venue_name}' with URL: {self.source_url} already exists. No update needed."
            )

        venue_obj.last_scraped_at = timezone.now()
        venue_obj.save(update_fields=["last_scraped_at"])

        return venue_obj

    def _process_game_types(self, data: PageData) -> dict[str, int]:
        # First, build a set of unique game types from the official games
        official_game_types = {game.type for game in data.venue_data.games}
        # Build another set containing custom ones found in event data
        custom_game_types = {event.game_type for event in data.event_data}

        logger.debug(
            f"Found {len(official_game_types)} official game types and {len(custom_game_types)} custom game types."
        )

        # Add them both to the db
        GameType.objects.bulk_create(
            [
                GameType(name=game_type)
                for game_type in (official_game_types | custom_game_types)
            ],
            ignore_conflicts=True,
        )

        # And query them back as a name -> pk lookup dict
        return dict(
            GameType.objects.filter(
                name__in=(official_game_types | custom_game_types)
            ).values_list("name", "pk")
        )

    def _process_games(
        self, data: PageData, game_types: dict[str, int]
    ) -> dict[tuple[str, int | None], Game]:
        # Now, create all Game entries for the venue
        Game.objects.bulk_create(
            [
                Game(
                    game_type_id=game_types[game.type],
                    day=game.day,
                    time=game.time,
                    venue=self.venue,
                )
                for game in data.venue_data.games
            ],
            ignore_conflicts=True,
        )

        # Create a set of tuple keys for official games
        # in the form (GameType pk, day)
        official_game_keys = {
            (game_types[game.type], game.day) for game in data.venue_data.games
        }

        # Determine any custom/unofficial games from event data
        custom_game_keys = {
            (game_types[event.game_type], event.date.weekday())
            for event in data.event_data
        } - official_game_keys

        # Reduce to just GameType pks
        custom_game_keys = {key[0] for key in custom_game_keys}

        # And add the remaining custom/unofficial ones
        Game.objects.bulk_create(
            [
                Game(
                    game_type_id=game_type,
                    venue=self.venue,
                )
                for game_type in custom_game_keys
            ],
            ignore_conflicts=True,
        )

        # And query them back as a lookup dict for use in _match_game_to_event
        conditions = Q()

        for game in data.venue_data.games:
            conditions |= Q(
                game_type_id=game_types[game.type],
                day=game.day,
                time=game.time,
                venue=self.venue,
            )

        for game_type_key in custom_game_keys:
            conditions |= Q(
                game_type_id=game_type_key,
                day__isnull=True,
                time__isnull=True,
                venue=self.venue,
            )

        games = {}
        for game in Game.objects.filter(conditions).select_related("game_type"):
            key = (game.game_type.name, game.day)
            if key in games:
                raise NotImplementedError(  # TODO: for multiple games on the same day, try to match based on order?
                    f"Multiple games found for '{game.game_type.name}' on day {game.day}. "
                    f"Time-based disambiguation not yet implemented."
                )
            games[key] = game

        return games

    def _process_quizmasters(self, event_data: list[EventData]) -> dict[str, int]:
        # Build a list of unique quizmasters
        unique_quizmaster_names = {event.quizmaster for event in event_data}

        # Add any new ones to the db
        Quizmaster.objects.bulk_create(
            [Quizmaster(name=name) for name in unique_quizmaster_names],
            ignore_conflicts=True,
        )

        # And query them back as a lookup dict: quizmaster.name -> pk
        return dict(
            Quizmaster.objects.filter(name__in=unique_quizmaster_names).values_list(
                "name", "pk"
            )
        )

    def _process_autoscrape_event(
        self,
        event_data: list[EventData],
        autoscrape_game_id: int | None,
        quizmasters: dict[str, int],
    ) -> list[EventData]:
        # Before handling regular events, if this is an
        # autoscrape call, try and update the placeholder event
        events_not_updated = event_data.copy()
        if not self.is_manual:
            matching_events = [
                e
                for e in event_data
                if self._match_game_to_event(
                    game_type=e.game_type, day=e.date.weekday()
                ).pk
                == autoscrape_game_id
            ]

            if len(matching_events) > 1:
                raise ValueError(
                    "Found multiple events in page data that match autoscraping game."
                )

            elif len(matching_events) == 1:
                matching_event = matching_events[0]

                event_obj = Event.objects.select_for_update().get(
                    game_id=autoscrape_game_id,
                    date=timezone.localdate(),  # This is kinda brittle and should probably be passed from the task
                    quizmaster__isnull=True,  # This is probably redundant given the unique constraint on the Event model
                )

                self.updated_event_pk = event_obj.pk

                event_obj.end_datetime = timezone.now()
                event_obj.description = matching_event.description
                event_obj.quizmaster_id = quizmasters[matching_event.quizmaster]  # pyright: ignore[reportAttributeAccessIssue]

                event_obj.save(
                    update_fields=["end_datetime", "description", "quizmaster"]
                )

                events_not_updated = [e for e in event_data if e is not matching_event]

                self.updated_event_data = matching_event

        return events_not_updated

    def _process_events(
        self,
        event_data: list[EventData],
        events_not_updated: list[EventData],
        quizmasters: dict[str, int],
    ) -> dict[tuple[int, date], int]:
        # Add each event instance for this venue's games
        Event.objects.bulk_create(
            [
                Event(
                    game=(
                        _game := self._match_game_to_event(  # Why use walrus here?
                            game_type=event.game_type,
                            day=event.date.weekday(),
                        )
                    ),
                    date=event.date,
                    end_datetime=None,
                    description=event.description,
                    quizmaster_id=quizmasters[event.quizmaster],
                )
                for event in events_not_updated
            ],
            ignore_conflicts=True,
        )

        # Query back the events that were just created
        # Match on game (which includes venue) and date for uniqueness
        # The duplication of calls to _match_game_to_event is probably
        # fine because of its cache
        conditions = Q()
        for event in event_data:
            conditions |= Q(
                game=self._match_game_to_event(
                    game_type=event.game_type,
                    day=event.date.weekday(),
                ),
                date=event.date,
            )

        return {
            (game_id, date): pk
            for game_id, date, pk in Event.objects.filter(conditions).values_list(
                "game_id", "date", "pk"
            )
        }

    def _process_official_teams(self, event_data: list[EventData]) -> dict[int, int]:
        # Starting with non-guest teams:
        #
        # Build a set of unique IDs
        unique_team_ids = {
            team.team_id
            for event in event_data
            for team in event.teams
            if team.team_id is not None
        }

        # Add them to the db
        Team.objects.bulk_create(
            [Team(team_id=team_id) for team_id in unique_team_ids],
            ignore_conflicts=True,
        )

        # Query back all teams in the set as a
        # lookup dict: team_id -> pk
        teams = dict(
            Team.objects.filter(team_id__in=unique_team_ids).values_list(
                "team_id", "pk"
            )
        )

        # Create all TeamName entries for the teams
        # and tie them to their respective Team entries
        TeamName.objects.bulk_create(
            [
                TeamName(
                    name=team_data.name,
                    team_id=teams[team_data.team_id],
                    guest=False,
                )
                for event in event_data
                for team_data in event.teams
                if team_data.team_id is not None
            ],
            ignore_conflicts=True,
        )

        return teams

    def _process_guest_teams(self, event_data: list[EventData]) -> dict[str, int]:
        # Now, handle guest teams:
        #
        # Build a set of unique guest team names
        unique_guest_team_names = {
            team.name
            for event in event_data
            for team in event.teams
            if team.team_id is None
        }

        existing_guest_teams = dict(
            Team.objects.filter(
                names__name__in=unique_guest_team_names, names__guest=True
            ).values_list("names__name", "pk")
        )

        # Retrieve existing guest team names
        existing_guest_team_names = existing_guest_teams.keys()

        # Determine the new guest teams to create
        new_guest_team_names = unique_guest_team_names - existing_guest_team_names

        # Create the required number of "blank" guest team objects
        blank_guest_teams = Team.objects.bulk_create(
            [Team() for _ in range(len(new_guest_team_names))],
        )

        # Finally, create TeamName entries for guest teams
        # Because guest Team objects have no team_id, we can
        # just pair them via enumeration
        new_name_objs = []
        new_guest_teams = {}
        for idx, team_name in enumerate(sorted(new_guest_team_names)):
            new_name_objs.append(
                TeamName(
                    name=team_name,
                    team=blank_guest_teams[idx],
                    guest=True,
                )
            )

            new_guest_teams[team_name] = blank_guest_teams[idx].pk

        TeamName.objects.bulk_create(new_name_objs)

        all_guest_teams = existing_guest_teams | new_guest_teams

        return all_guest_teams

    def _process_autoscrape_teps(self) -> None:
        # If this is an autoscrape call, update any existing
        # TeamEventParticipation entries with their proper scores
        if not self.is_manual and self.updated_event_data is not None:
            teps_to_update = (
                TeamEventParticipation.objects.filter(
                    event_id=self.updated_event_pk, score__isnull=True
                )
                .select_related("team", "team_name")
                .select_for_update()
            )

            score_dict = {
                (team.team_id, team.name): team.score
                for team in self.updated_event_data.teams
            }

            for tep in teps_to_update:
                key = (tep.team.team_id, tep.team_name.name)
                if key not in score_dict:
                    raise ValueError(
                        "Unable to match existing TeamEventParticipation to scraped data for score update. "
                        "Did you attach the wrong team to the placeholder event? "
                        f"Key: {key}"
                    )

                tep.score = score_dict[key]
                tep.save(update_fields=["score"])

        # TODO: Instead of relying on bulk_create with ignore_conflicts=True,
        #       exclude updated TeamEventParticipation entries from the bulk_create

    def _process_team_event_participations(
        self,
        event_data: list[EventData],
        events: dict[tuple[int, date], int],
        teams: dict[int, int],
        guest_teams: dict[str, int],
    ) -> None:
        # Last but not least, TeamEventParticipation
        #
        # Create lookup dict: (Team pk, Team Name str) -> TeamName pk
        team_names = {
            (team_id, name): pk
            for team_id, name, pk in TeamName.objects.filter(
                Q(team_id__in=teams.values()) | Q(team_id__in=guest_teams.values())
            ).values_list("team_id", "name", "pk")
        }

        # The goal here is really just to select the highest score among
        # any duplicate TeamEventParticipations that may have been scraped
        unique_teps = {}
        for event in event_data:
            event_id = events[
                (
                    self._match_game_to_event(
                        game_type=event.game_type,
                        day=event.date.weekday(),
                    ).pk,
                    event.date,
                )
            ]
            for team in event.teams:
                _team = (
                    teams[team.team_id]
                    if team.team_id is not None
                    else guest_teams[team.name]
                )

                key = (_team, event_id)

                if key not in unique_teps or team.score > unique_teps[key].score:
                    unique_teps[key] = TeamEventParticipation(
                        team_id=_team,
                        team_name_id=team_names[(_team, team.name)],
                        event_id=event_id,
                        score=team.score,
                    )

        TeamEventParticipation.objects.bulk_create(
            unique_teps.values(),
            ignore_conflicts=True,
        )
