from django.contrib import admin
from .models import Profile, SpotifyWrappedData
# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'spotify_user_id')
    search_fields = ('user__username', 'spotify_user_id')

@admin.register(SpotifyWrappedData)
class SpotifyWrappedDataAdmin(admin.ModelAdmin):
    list_display = ('user', 'wrapped_id', 'created_at')
    search_fields = ('wrapped_id', 'user__user__username')
    readonly_fields = ('created_at',)