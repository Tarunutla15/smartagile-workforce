"""
Fix InconsistentMigrationHistory:

  Migration account.0001_initial is applied before its dependency accounts.0001_initial

This happens when django-allauth's `account` app was migrated before the custom
`accounts` app existed (AUTH_USER_MODEL = accounts.User).

If you see authtoken.0001_initial (or tasks) applied before accounts.0001_initial
on a DB that still has stock auth_user and no accounts_user, use instead:

  python manage.py repair_legacy_auth_to_accounts
  python manage.py migrate

Usage (from backend/, venv active):

  python manage.py repair_accounts_dependency
  python manage.py migrate
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone


class Command(BaseCommand):
    help = "Repair migration order between accounts.User and allauth account app."

    def handle(self, *args, **options):
        table_names = set(connection.introspection.table_names())
        has_user_table = "accounts_user" in table_names

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
                ["accounts", "0001_initial"],
            )
            has_migration_row = cursor.fetchone() is not None

        if has_migration_row and has_user_table:
            self.stdout.write(
                self.style.SUCCESS(
                    "accounts.0001_initial is already applied and accounts_user exists. "
                    "Run: python manage.py migrate"
                )
            )
            return

        if has_user_table and not has_migration_row:
            self.stdout.write(
                "accounts_user exists but django_migrations is missing accounts.0001_initial — recording it."
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                    ["accounts", "0001_initial", timezone.now()],
                )
            self.stdout.write(self.style.SUCCESS("Recorded. Run: python manage.py migrate"))
            return

        # Table missing: apply accounts.0001 while consistency check is bypassed
        self.stdout.write("Creating accounts_user (accounts.0001_initial)...")

        _real = MigrationLoader.check_consistent_history

        def _skip_consistency(self, conn):
            return

        MigrationLoader.check_consistent_history = _skip_consistency
        try:
            call_command("migrate", "accounts", "0001", interactive=False, verbosity=1)
        finally:
            MigrationLoader.check_consistent_history = _real

        self.stdout.write(self.style.SUCCESS("Done. Run: python manage.py migrate"))
