from math import ceil
from typing import TYPE_CHECKING, Any, override

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from model_bakery import baker

from api.models import (
    # Answer,
    Event,
    Game,
    GameType,
    Glossary,
    Member,
    MemberAttendance,
    Question,
    Quizmaster,
    Round,
    RoundType,
    Table,
    Team,
    TeamEventParticipation,
    TeamName,
    Theme,
    Venue,
    Vote,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    help = "Seed the database with placeholder data"

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force seeding even when DEBUG is False.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Clear existing data before seeding.",
        )
        parser.add_argument(
            "--scalar",
            type=float,
            default=1.0,
            help=(
                "Scalar to use for scaling the amount of seeded data "
                "(e.g. 0.5 for half as much, 2 for twice as much)."
            ),
        )
        parser.add_argument(
            "--model",
            metavar="MODEL",
            type=str,
            required=False,
            help="The specific model to seed (optional).",
        )

    @override
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            self.stdout.write(
                self.style.ERROR(
                    "Seeding data should only be done in development. "
                    "Use --force to override.",
                ),
            )
            return

        if options["flush"]:
            self.stdout.write("Clearing existing data...")
            self._flush()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        if options["scalar"] <= 0:
            self.stdout.write(
                self.style.WARNING("Scalar of zero or less, no data will be seeded."),
            )
            return

        self.stdout.write("Seeding data...")

        self._seed(scalar=options["scalar"])

        self.stdout.write(self.style.SUCCESS("Data seeded successfully."))

    def _seed(self, scalar: float) -> None:
        fake = Faker()
        with transaction.atomic():
            baker.make(Quizmaster, name=fake.unique.name, _quantity=ceil(10 * scalar))

            baker.make(
                Theme,
                name=lambda: fake.unique.word(part_of_speech="noun").capitalize(),
                _quantity=ceil(50 * scalar),
            )

            baker.make(
                RoundType,
                number=baker.seq(value=0),
                name=lambda: fake.unique.word(part_of_speech="noun").capitalize(),
                double_or_nothing=lambda: fake.boolean(chance_of_getting_true=85),
                _quantity=8,
            )

            baker.make(Member, name=fake.unique.first_name, _quantity=ceil(15 * scalar))

            # fake.type

    def _flush(self) -> None:
        models_to_delete = [
            # Answer,
            Event,
            Game,
            GameType,
            Glossary,
            Member,
            MemberAttendance,
            Question,
            Quizmaster,
            Round,
            RoundType,
            Table,
            Team,
            TeamEventParticipation,
            TeamName,
            Theme,
            Venue,
            Vote,
        ]

        deleted_counts = {
            model._meta.label: model.objects.all().delete()[0]  # noqa: SLF001
            for model in models_to_delete
        }

        for label, count in deleted_counts.items():
            self.stdout.write(f"Deleted {count} {label}.")
