from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from model_bakery import baker

from .models import (
    Quizmaster,
    Team,
    Member,
    Table,
    Theme,
    Round,
    Glossary,
    EventType,
    Venue,
    Event,
    Vote,
    TeamEventParticipation,
    MemberAttendance,
)


class QuizmasterModelTest(TestCase):
    def test_create_quizmaster(self):
        """Test creating a quizmaster with model_bakery"""
        quizmaster = baker.make(Quizmaster)
        self.assertIsNotNone(quizmaster.pk)
        self.assertIsNotNone(quizmaster.name)
        self.assertIsNotNone(quizmaster.created_at)
        self.assertIsNotNone(quizmaster.updated_at)

    def test_quizmaster_str(self):
        """Test quizmaster string representation"""
        quizmaster = baker.make(Quizmaster, name="John Doe")
        self.assertEqual(str(quizmaster), "John Doe")

    def test_quizmaster_unique_name(self):
        """Test that quizmaster names must be unique"""
        baker.make(Quizmaster, name="John Doe")
        with self.assertRaises(IntegrityError):
            baker.make(Quizmaster, name="John Doe")


class TeamModelTest(TestCase):
    def test_create_team(self):
        """Test creating a team with model_bakery"""
        team = baker.make(Team)
        self.assertIsNotNone(team.pk)
        self.assertIsNotNone(team.name)
        self.assertIsNotNone(team.created_at)
        self.assertIsNotNone(team.updated_at)

    def test_team_with_team_id(self):
        """Test team with team_id"""
        team = baker.make(Team, name="Test Team", team_id=123)
        self.assertEqual(team.team_id, 123)
        self.assertIn("123", str(team))
        self.assertIn("Test Team", str(team))

    def test_team_without_team_id(self):
        """Test team without team_id (guest)"""
        team = baker.make(Team, name="Guest Team", team_id=None)
        self.assertIsNone(team.team_id)
        self.assertIn("Guest", str(team))
        self.assertIn("Guest Team", str(team))

    def test_team_long_name_truncation_in_str(self):
        """Test that long team names are truncated in string representation"""
        long_name = "A" * 150
        team = baker.make(Team, name=long_name)
        str_repr = str(team)
        self.assertIn("...", str_repr)

    def test_team_unique_name(self):
        """Test that team names must be unique"""
        baker.make(Team, name="Unique Team")
        with self.assertRaises(IntegrityError):
            baker.make(Team, name="Unique Team")

    def test_team_unique_team_id(self):
        """Test that team_id must be unique when not null"""
        baker.make(Team, team_id=456)
        with self.assertRaises(IntegrityError):
            baker.make(Team, team_id=456)


class MemberModelTest(TestCase):
    def test_create_member(self):
        """Test creating a member with model_bakery"""
        member = baker.make(Member)
        self.assertIsNotNone(member.pk)
        self.assertIsNotNone(member.name)
        self.assertIsNotNone(member.team)
        self.assertIsNotNone(member.created_at)
        self.assertIsNotNone(member.updated_at)

    def test_member_str(self):
        """Test member string representation"""
        member = baker.make(Member, name="Jane Smith")
        self.assertEqual(str(member), "Jane Smith")

    def test_member_team_relationship(self):
        """Test member belongs to a team"""
        team = baker.make(Team)
        member = baker.make(Member, team=team)
        self.assertEqual(member.team, team)
        self.assertIn(member, team.members.all())

    def test_member_unique_constraint(self):
        """Test unique constraint for name and team"""
        team = baker.make(Team)
        baker.make(Member, name="John", team=team)
        with self.assertRaises(IntegrityError):
            baker.make(Member, name="John", team=team)

    def test_member_cascade_delete_with_team(self):
        """Test that members are deleted when team is deleted"""
        team = baker.make(Team)
        member = baker.make(Member, team=team)
        member_pk = member.pk
        team.delete()
        self.assertFalse(Member.objects.filter(pk=member_pk).exists())


class TableModelTest(TestCase):
    def test_create_table(self):
        """Test creating a table with model_bakery"""
        table = baker.make(Table)
        self.assertIsNotNone(table.pk)
        self.assertIsNotNone(table.table_id)
        self.assertIsNotNone(table.created_at)
        self.assertIsNotNone(table.updated_at)

    def test_table_with_name(self):
        """Test table with name"""
        table = baker.make(Table, table_id=1, name="Table A")
        self.assertEqual(str(table), "Table A")

    def test_table_without_name(self):
        """Test table without name uses table_id"""
        table = baker.make(Table, table_id=42, name=None)
        self.assertEqual(str(table), "42")

    def test_table_is_upstairs(self):
        """Test table upstairs flag"""
        table = baker.make(Table, is_upstairs=True)
        self.assertTrue(table.is_upstairs)

    def test_table_unique_table_id(self):
        """Test that table_id must be unique"""
        baker.make(Table, table_id=10)
        with self.assertRaises(IntegrityError):
            baker.make(Table, table_id=10)

    def test_table_unique_name(self):
        """Test that table name must be unique when not null"""
        baker.make(Table, name="VIP Booth")
        with self.assertRaises(IntegrityError):
            baker.make(Table, name="VIP Booth")


class ThemeModelTest(TestCase):
    def test_create_theme(self):
        """Test creating a theme with model_bakery"""
        theme = baker.make(Theme)
        self.assertIsNotNone(theme.pk)
        self.assertIsNotNone(theme.name)
        self.assertIsNotNone(theme.created_at)
        self.assertIsNotNone(theme.updated_at)

    def test_theme_str(self):
        """Test theme string representation"""
        theme = baker.make(Theme, name="80s Music")
        self.assertEqual(str(theme), "80s Music")

    def test_theme_unique_name(self):
        """Test that theme names must be unique"""
        baker.make(Theme, name="Sports")
        with self.assertRaises(IntegrityError):
            baker.make(Theme, name="Sports")


class RoundModelTest(TestCase):
    def test_create_round(self):
        """Test creating a round with model_bakery"""
        round_obj = baker.make(Round)
        self.assertIsNotNone(round_obj.pk)
        self.assertIsNotNone(round_obj.number)
        self.assertIsNotNone(round_obj.name)
        self.assertIsNotNone(round_obj.created_at)
        self.assertIsNotNone(round_obj.updated_at)

    def test_round_str(self):
        """Test round string representation"""
        round_obj = baker.make(Round, number=1, name="General Knowledge")
        self.assertEqual(str(round_obj), "Round 1: General Knowledge")

    def test_round_unique_number(self):
        """Test that round number must be unique"""
        baker.make(Round, number=1)
        with self.assertRaises(IntegrityError):
            baker.make(Round, number=1)

    def test_round_unique_name(self):
        """Test that round name must be unique"""
        baker.make(Round, name="Music Round")
        with self.assertRaises(IntegrityError):
            baker.make(Round, name="Music Round")


class GlossaryModelTest(TestCase):
    def test_create_glossary(self):
        """Test creating a glossary entry with model_bakery"""
        glossary = baker.make(Glossary)
        self.assertIsNotNone(glossary.pk)
        self.assertIsNotNone(glossary.acronym)
        self.assertIsNotNone(glossary.definition)
        self.assertIsNotNone(glossary.created_at)
        self.assertIsNotNone(glossary.updated_at)

    def test_glossary_str_short_definition(self):
        """Test glossary string representation with short definition"""
        glossary = baker.make(Glossary, acronym="FAQ", definition="Frequently Asked Questions")
        self.assertEqual(str(glossary), "FAQ | Frequently Asked Questions")

    def test_glossary_str_long_definition(self):
        """Test glossary string representation with long definition"""
        long_def = "A" * 150
        glossary = baker.make(Glossary, acronym="TEST", definition=long_def)
        str_repr = str(glossary)
        self.assertIn("TEST", str_repr)
        self.assertIn("...", str_repr)

    def test_glossary_unique_acronym(self):
        """Test that acronym must be unique"""
        baker.make(Glossary, acronym="API")
        with self.assertRaises(IntegrityError):
            baker.make(Glossary, acronym="API")


class EventTypeModelTest(TestCase):
    def test_create_event_type(self):
        """Test creating an event type with model_bakery"""
        event_type = baker.make(EventType)
        self.assertIsNotNone(event_type.pk)
        self.assertIsNotNone(event_type.name)
        self.assertIsNotNone(event_type.created_at)
        self.assertIsNotNone(event_type.updated_at)

    def test_event_type_str(self):
        """Test event type string representation"""
        event_type = baker.make(EventType, name="Trivia Night")
        self.assertEqual(str(event_type), "Trivia Night")

    def test_event_type_unique_name(self):
        """Test that event type names must be unique"""
        baker.make(EventType, name="Quiz")
        with self.assertRaises(IntegrityError):
            baker.make(EventType, name="Quiz")


class VenueModelTest(TestCase):
    def test_create_venue(self):
        """Test creating a venue with model_bakery"""
        venue = baker.make(Venue)
        self.assertIsNotNone(venue.pk)
        self.assertIsNotNone(venue.name)
        self.assertIsNotNone(venue.url)
        self.assertIsNotNone(venue.created_at)
        self.assertIsNotNone(venue.updated_at)

    def test_venue_str(self):
        """Test venue string representation"""
        venue = baker.make(Venue, name="The Pub")
        self.assertEqual(str(venue), "The Pub")

    def test_venue_unique_name(self):
        """Test that venue names must be unique"""
        baker.make(Venue, name="Bar XYZ")
        with self.assertRaises(IntegrityError):
            baker.make(Venue, name="Bar XYZ")

    def test_venue_unique_url(self):
        """Test that venue URLs must be unique"""
        baker.make(Venue, url="https://example.com")
        with self.assertRaises(IntegrityError):
            baker.make(Venue, url="https://example.com")


class EventModelTest(TestCase):
    def test_create_event(self):
        """Test creating an event with model_bakery"""
        event = baker.make(Event)
        self.assertIsNotNone(event.pk)
        self.assertIsNotNone(event.venue)
        self.assertIsNotNone(event.game_type)
        self.assertIsNotNone(event.start_datetime)
        self.assertIsNotNone(event.quizmaster)
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)

    def test_event_str_with_theme(self):
        """Test event string representation with theme"""
        venue = baker.make(Venue, name="Test Venue")
        quizmaster = baker.make(Quizmaster, name="Quiz Master")
        theme = baker.make(Theme, name="History")
        event = baker.make(
            Event,
            venue=venue,
            quizmaster=quizmaster,
            theme=theme,
            start_datetime=timezone.now(),
        )
        str_repr = str(event)
        self.assertIn("Test Venue", str_repr)
        self.assertIn("Quiz Master", str_repr)
        self.assertIn("History", str_repr)

    def test_event_str_without_theme(self):
        """Test event string representation without theme"""
        venue = baker.make(Venue, name="Test Venue")
        quizmaster = baker.make(Quizmaster, name="Quiz Master")
        event = baker.make(
            Event,
            venue=venue,
            quizmaster=quizmaster,
            theme=None,
            start_datetime=timezone.now(),
        )
        str_repr = str(event)
        self.assertIn("Test Venue", str_repr)
        self.assertIn("Quiz Master", str_repr)
        self.assertNotIn("History", str_repr)

    def test_event_relationships(self):
        """Test event foreign key relationships"""
        event = baker.make(Event)
        self.assertIsInstance(event.venue, Venue)
        self.assertIsInstance(event.game_type, EventType)
        self.assertIsInstance(event.quizmaster, Quizmaster)

    def test_event_optional_fields(self):
        """Test event optional fields"""
        event = baker.make(Event, end_datetime=None, description=None, theme=None, quizmaster_table=None)
        self.assertIsNone(event.end_datetime)
        self.assertIsNone(event.description)
        self.assertIsNone(event.theme)
        self.assertIsNone(event.quizmaster_table)

    def test_event_unique_constraint(self):
        """Test unique constraint for venue, game_type, and start_datetime"""
        venue = baker.make(Venue)
        game_type = baker.make(EventType)
        start_time = timezone.now()
        baker.make(Event, venue=venue, game_type=game_type, start_datetime=start_time)
        with self.assertRaises(IntegrityError):
            baker.make(Event, venue=venue, game_type=game_type, start_datetime=start_time)


class VoteModelTest(TestCase):
    def test_create_vote(self):
        """Test creating a vote with model_bakery"""
        vote = baker.make(Vote)
        self.assertIsNotNone(vote.pk)
        self.assertIsNotNone(vote.member)
        self.assertIsNotNone(vote.vote)
        self.assertIsNotNone(vote.event)
        self.assertIsNotNone(vote.round)
        self.assertIsNotNone(vote.created_at)
        self.assertIsNotNone(vote.updated_at)

    def test_vote_choices(self):
        """Test vote choices"""
        vote_right = baker.make(Vote, vote=Vote.RIGHT)
        vote_wrong = baker.make(Vote, vote=Vote.WRONG)
        vote_abstained = baker.make(Vote, vote=Vote.ABSTAINED)
        
        self.assertEqual(vote_right.vote, "R")
        self.assertEqual(vote_wrong.vote, "W")
        self.assertEqual(vote_abstained.vote, "A")
        
        self.assertEqual(vote_right.get_vote_display(), "Right")
        self.assertEqual(vote_wrong.get_vote_display(), "Wrong")
        self.assertEqual(vote_abstained.get_vote_display(), "Abstained")

    def test_vote_str(self):
        """Test vote string representation"""
        member = baker.make(Member, name="Test Member")
        event = baker.make(Event)
        vote = baker.make(Vote, member=member, event=event, vote=Vote.RIGHT)
        str_repr = str(vote)
        self.assertIn("Test Member", str_repr)
        self.assertIn("Right", str_repr)

    def test_vote_double_or_nothing(self):
        """Test double or nothing flag"""
        vote = baker.make(Vote, is_double_or_nothing=True)
        self.assertTrue(vote.is_double_or_nothing)

    def test_vote_relationships(self):
        """Test vote foreign key relationships"""
        vote = baker.make(Vote)
        self.assertIsInstance(vote.member, Member)
        self.assertIsInstance(vote.event, Event)
        self.assertIsInstance(vote.round, Round)

    def test_vote_unique_constraint(self):
        """Test unique constraint for member, event, and round"""
        member = baker.make(Member)
        event = baker.make(Event)
        round_obj = baker.make(Round)
        baker.make(Vote, member=member, event=event, round=round_obj)
        with self.assertRaises(IntegrityError):
            baker.make(Vote, member=member, event=event, round=round_obj)


class TeamEventParticipationModelTest(TestCase):
    def test_create_team_event_participation(self):
        """Test creating a team event participation with model_bakery"""
        participation = baker.make(TeamEventParticipation)
        self.assertIsNotNone(participation.pk)
        self.assertIsNotNone(participation.team)
        self.assertIsNotNone(participation.event)
        self.assertIsNotNone(participation.score)
        self.assertIsNotNone(participation.created_at)
        self.assertIsNotNone(participation.updated_at)

    def test_team_event_participation_str_with_table(self):
        """Test participation string representation with table"""
        team = baker.make(Team, name="Test Team")
        event = baker.make(Event)
        table = baker.make(Table, name="Table 1")
        participation = baker.make(
            TeamEventParticipation,
            team=team,
            event=event,
            table=table,
            score=50,
        )
        str_repr = str(participation)
        self.assertIn("Test Team", str_repr)
        self.assertIn("50 points", str_repr)
        self.assertIn("Table 1", str_repr)

    def test_team_event_participation_str_without_table(self):
        """Test participation string representation without table"""
        team = baker.make(Team, name="Test Team")
        event = baker.make(Event)
        participation = baker.make(
            TeamEventParticipation,
            team=team,
            event=event,
            table=None,
            score=50,
        )
        str_repr = str(participation)
        self.assertIn("Test Team", str_repr)
        self.assertIn("50 points", str_repr)
        self.assertNotIn("at", str_repr)

    def test_team_event_participation_relationships(self):
        """Test participation foreign key relationships"""
        participation = baker.make(TeamEventParticipation)
        self.assertIsInstance(participation.team, Team)
        self.assertIsInstance(participation.event, Event)

    def test_team_event_participation_unique_constraint(self):
        """Test unique constraint for team and event"""
        team = baker.make(Team)
        event = baker.make(Event)
        baker.make(TeamEventParticipation, team=team, event=event)
        with self.assertRaises(IntegrityError):
            baker.make(TeamEventParticipation, team=team, event=event)


class MemberAttendanceModelTest(TestCase):
    def test_create_member_attendance(self):
        """Test creating a member attendance with model_bakery"""
        attendance = baker.make(MemberAttendance)
        self.assertIsNotNone(attendance.pk)
        self.assertIsNotNone(attendance.member)
        self.assertIsNotNone(attendance.event)
        self.assertIsNotNone(attendance.created_at)
        self.assertIsNotNone(attendance.updated_at)

    def test_member_attendance_with_notes(self):
        """Test member attendance with notes"""
        attendance = baker.make(MemberAttendance, notes="Arrived late")
        self.assertEqual(attendance.notes, "Arrived late")

    def test_member_attendance_without_notes(self):
        """Test member attendance without notes"""
        attendance = baker.make(MemberAttendance, notes=None)
        self.assertIsNone(attendance.notes)

    def test_member_attendance_relationships(self):
        """Test attendance foreign key relationships"""
        attendance = baker.make(MemberAttendance)
        self.assertIsInstance(attendance.member, Member)
        self.assertIsInstance(attendance.event, Event)

    def test_member_attendance_unique_constraint(self):
        """Test unique constraint for member and event"""
        member = baker.make(Member)
        event = baker.make(Event)
        baker.make(MemberAttendance, member=member, event=event)
        with self.assertRaises(IntegrityError):
            baker.make(MemberAttendance, member=member, event=event)
