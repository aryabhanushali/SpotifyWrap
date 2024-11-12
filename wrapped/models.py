from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    spotify_user_id = models.CharField(max_length=255, blank=True, null=True)
    spotify_access_token = models.CharField(max_length=255, blank=True, null=True)
    spotify_refresh_token = models.CharField(max_length=255, blank=True, null=True)
    token_expiry = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class SpotifyWrappedData(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    wrapped_id = models.CharField(max_length=10, unique=True)
    top_tracks = models.JSONField()  # Store track data as JSON
    top_artists = models.JSONField()  # Store artist data as JSON
    top_genres = models.JSONField()  # Store genre data as JSON
    total_time_listened = models.IntegerField()  # Store total time listened
    created_at = models.DateTimeField(auto_now_add=True)

