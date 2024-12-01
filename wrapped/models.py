from django.db import models
from django.contrib.auth.models import User

from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    A model representing the user's profile, including integration with Spotify.

    The Profile model is linked to the User model and stores Spotify-specific information,
    such as the user's Spotify ID and access token for authentication.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    """
    A one-to-one relationship with the User model. Each user can have one profile.
    """

    spotify_user_id = models.CharField(max_length=255, blank=True, null=True)
    """
    Stores the unique Spotify user ID for this profile. This is used to make requests 
    to the Spotify API on behalf of the user.
    """

    spotify_access_token = models.CharField(max_length=255, blank=True, null=True)
    """
    Stores the access token required for making authenticated requests to the Spotify API.
    The token can be used to retrieve the user's Spotify data.
    """


class SpotifyWrappedData(models.Model):
    """
    A model that stores a user's Spotify Wrapped data, including their top tracks,
    top artists, top genres, and total listening time. Each record is linked to a user profile.

    The model also allows customization through the 'custom_name' field.
    """

    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    """
    A foreign key relationship to the Profile model. Each SpotifyWrappedData entry 
    is associated with a specific user profile.
    """

    wrapped_id = models.CharField(max_length=10, unique=True)
    """
    A unique identifier for the user's Spotify Wrapped data. This is used to distinguish 
    each wrapped year or data set.
    """

    top_tracks = models.JSONField()
    """
    A JSON field to store the user's top tracks. This field will contain track data in JSON format,
    which includes details like song name, artist, and listening count.
    """

    top_artists = models.JSONField()
    """
    A JSON field to store the user's top artists. This field contains artist data in JSON format, 
    including the artist name and listening count.
    """

    top_genres = models.JSONField()
    """
    A JSON field to store the user's top genres. This field includes genre data in JSON format,
    which may include genre names and listening count.
    """

    total_time_listened = models.IntegerField()
    """
    An integer field representing the total time (in minutes or seconds) the user has spent listening 
    to music during the period the Wrapped data represents.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    """
    Automatically records the timestamp when the SpotifyWrappedData record is created.
    This helps track when each wrapped data set was generated.
    """

    custom_name = models.CharField(max_length=255, blank=True, null=True)
    """
    An optional field for giving a custom name to the Spotify Wrapped data. This can be used to 
    personalize the wrapped data, for example, '2023 Year In Review' or 'My Spotify Wrapped'.
    """

