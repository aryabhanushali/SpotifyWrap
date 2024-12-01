from django.apps import AppConfig


class WrappedConfig(AppConfig):
    """
    Configuration for the 'wrapped' Django application.

    This class sets up metadata and default configurations for the 'wrapped' app.

    Attributes:
        default_auto_field (str): Specifies the default type of primary key field to use
                                  for models in the app. Defaults to 'BigAutoField' for
                                  auto-incrementing integers.
        name (str): The name of the application. This should match the app folder name.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wrapped'
