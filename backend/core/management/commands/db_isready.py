import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Check if the database is ready"

    def handle(self, *args, **options):
        db_alias = getattr(settings, "HEALTHCHECK_MIGRATIONS_DB", DEFAULT_DB_ALIAS)

        try:
            executor = MigrationExecutor(connections[db_alias])
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if not plan:
                self.stdout.write(self.style.SUCCESS("Database is ready and migrated."))
                sys.exit(0)
            else:
                self.stderr.write(
                    self.style.WARNING("Database has unapplied migrations.")
                )
                sys.exit(1)
        except DatabaseError:
            self.stderr.write(self.style.ERROR("Database is not ready."))
            sys.exit(2)
        except Exception:
            self.stderr.write(self.style.ERROR("Unexpected error."))
            sys.exit(3)
