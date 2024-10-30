from django.db import models
from django.contrib.auth.models import User

class SpotifyWrappedData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wrapped_id = models.CharField(max_length=10, unique=True)
    top_tracks = models.JSONField()  # Store track data as JSON
    top_artists = models.JSONField()  # Store artist data as JSON
    top_genres = models.JSONField()  # Store genre data as JSON
    total_time_listened = models.IntegerField()  # Store total time listened
    created_at = models.DateTimeField(auto_now_add=True)
