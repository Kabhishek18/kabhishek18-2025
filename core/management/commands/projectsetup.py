# kabhishek18-2025/core/management/commands/projectsetup.py
# python manage.py projectsetup init
# python manage.py projectsetup resetdb
# python manage.py projectsetup resetapp core

import os
import time
from argparse import ArgumentParser

import MySQLdb
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import utils
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Helper Functions ---

def get_db_connection(db_name=None):
    """
    Creates a direct connection to the MySQL server.
    If db_name is None, it connects to the server itself without selecting a database.
    This is necessary to create or drop databases.
    """
    kwargs = {
        'host': settings.DATABASES['default'].get('HOST', 'localhost'),
        'port': int(settings.DATABASES['default'].get('PORT', 3306)),
        'user': settings.DATABASES['default'].get('USER', 'root'),
        'passwd': settings.DATABASES['default'].get('PASSWORD', ''),
    }
    if db_name:
        kwargs['db'] = db_name
    return MySQLdb.connect(**kwargs)


def execute_sql(cursor, sql):
    """Executes SQL and prints feedback."""
    try:
        cursor.execute(sql)
        print(f"✅ Executed: {sql}")
    except Exception as e:
        print(f"❌ Could not execute '{sql}': {e}")


class Command(BaseCommand):
    help = "A custom command to automate project setup and management."

    def add_arguments(self, parser: ArgumentParser):
        """
        Adds sub-commands for our main command.
        """
        subparsers = parser.add_subparsers(dest="command", required=True)

        # Sub-command for initial project setup
        subparsers.add_parser("init", help="Initializes the project: creates DB, runs migrations, creates superuser.")
        
        # Sub-command to completely reset the database
        subparsers.add_parser("resetdb", help="Resets the database: drops, recreates, and migrates.")

        # Sub-command to reset a specific app's migrations
        parser_resetapp = subparsers.add_parser("resetapp", help="Resets a specific app: reverts all its migrations.")
        parser_resetapp.add_argument("app_label", type=str, help="The label of the app to reset (e.g., 'core').")

    def handle(self, *args, **options):
        """
        The main entry point for the management command.
        """
        command = options["command"]

        if command == "init":
            self.init_project()
        elif command == "resetdb":
            self.reset_database()
        elif command == "resetapp":
            self.reset_app(options["app_label"])

    def init_project(self):
        """
        Handles the 'init' command to set up the project from scratch.
        """
        self.stdout.write(self.style.SUCCESS("\n🚀 Starting Initial Project Setup..."))
        db_name = settings.DATABASES['default']['NAME']

        # Step 1: Create the database
        self.stdout.write(self.style.HTTP_INFO(f"\n[1/4] Creating database '{db_name}'..."))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            execute_sql(cursor, f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f"Database '{db_name}' is ready."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Database creation failed: {e}"))
            return

        # Step 2: Run makemigrations
        self.stdout.write(self.style.HTTP_INFO("\n[2/4] Creating new migrations..."))
        call_command("makemigrations")

        # Step 3: Run migrate
        self.stdout.write(self.style.HTTP_INFO("\n[3/4] Applying migrations..."))
        call_command("migrate")

        # Step 4: Create superuser from environment variables
        self.stdout.write(self.style.HTTP_INFO("\n[4/4] Creating superuser..."))
        self.create_superuser()

        self.stdout.write(self.style.SUCCESS("\n🎉 Project initialization complete!"))

    def reset_database(self):
        """
        Handles the 'resetdb' command to drop and recreate the database.
        """
        self.stdout.write(self.style.WARNING("\n🔥 Resetting entire database... THIS IS DESTRUCTIVE!"))
        db_name = settings.DATABASES['default']['NAME']
        
        # Confirmation prompt
        confirm = input(f"Are you sure you want to drop and recreate the '{db_name}' database? [y/N]: ")
        if confirm.lower() != 'y':
            self.stdout.write(self.style.SUCCESS("Database reset cancelled."))
            return
            
        # Step 1: Drop and Recreate the database
        self.stdout.write(self.style.HTTP_INFO(f"\n[1/2] Dropping and recreating database '{db_name}'..."))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            execute_sql(cursor, f"DROP DATABASE IF EXISTS {db_name};")
            execute_sql(cursor, f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f"Database '{db_name}' has been reset."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Database reset failed: {e}"))
            return

        # Step 2: Run migrate
        self.stdout.write(self.style.HTTP_INFO("\n[2/2] Applying migrations to the new database..."))
        call_command("migrate")
        
        self.stdout.write(self.style.SUCCESS("\n🎉 Database reset complete!"))
        self.stdout.write(self.style.WARNING("Don't forget to create a new superuser with 'python manage.py projectsetup init' or 'python manage.py createsuperuser'."))

    def reset_app(self, app_label):
        """
        Handles the 'resetapp' command to revert all migrations for a specific app.
        """
        self.stdout.write(self.style.WARNING(f"\n🔥 Resetting app '{app_label}'... THIS IS DESTRUCTIVE!"))
        
        # Confirmation prompt
        confirm = input(f"Are you sure you want to revert all migrations for '{app_label}'? [y/N]: ")
        if confirm.lower() != 'y':
            self.stdout.write(self.style.SUCCESS("App reset cancelled."))
            return
            
        self.stdout.write(self.style.HTTP_INFO(f"\n[1/2] Reverting all migrations for '{app_label}'..."))
        try:
            # `migrate zero` reverts all migrations for the app
            call_command("migrate", app_label, "zero")
            self.stdout.write(self.style.SUCCESS(f"Successfully reverted migrations for '{app_label}'."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Could not revert migrations: {e}"))
            return

        self.stdout.write(self.style.HTTP_INFO(f"\n[2/2] Re-applying migrations for '{app_label}'..."))
        call_command("migrate", app_label)
        
        self.stdout.write(self.style.SUCCESS(f"\n🎉 App '{app_label}' reset complete!"))
        
    def create_superuser(self):
        """
        Creates a superuser non-interactively from environment variables.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "Panda")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "developer@kabhishek18.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "D2[Z9b+{x*+,.&B,XW6h")

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists. Skipping creation."))

