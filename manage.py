#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.
"""
import os
import sys


def main():
    """
    Set up the Django environment and execute administrative commands.

    This function configures the `DJANGO_SETTINGS_MODULE` environment variable to the default settings
    for the project and then executes the command-line interface for Django. It also handles ImportErrors
    in case Django is not properly installed or available.

    Raises:
        ImportError: Raised if Django is not installed or cannot be imported.
    """
    # Set the default Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SpotifyWrapped.settings')
    try:
        # Import Django's execute_from_command_line utility
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Raise an error if Django is not installed or available
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Execute the command-line arguments passed to the script
    execute_from_command_line(sys.argv)


# Entry point of the script
if __name__ == '__main__':
    main()
