import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import JsonResponse
from urllib.parse import urlencode
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.db import IntegrityError
import datetime
import random
import string
from .models import SpotifyWrappedData, Profile


# Create your views here.
def home(request):
    return render(request, "wrapped/home.html")

def spotify_login(request):
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "show_dialog": "true",
        "scope": "user-top-read",  # Request permission to read top songs and artists
    }
    url = f"{auth_url}?{urlencode(params)}"
    return redirect(url)


def spotify_logout(request):
    # Clear Spotify-related session data
    request.session.pop("access_token", None)
    request.session.pop("refresh_token", None)
    print(request.session.get("access_token"))
    return redirect("home")


def spotify_callback(request):
    code = request.GET.get('code')

    if not code:
        return HttpResponse('Error: No authorization code received', status=400)

    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
            'client_id': settings.SPOTIFY_CLIENT_ID,
            'client_secret': settings.SPOTIFY_CLIENT_SECRET
        }
    )

    data = response.json()
    access_token = data.get('access_token')
    if not access_token:
        return HttpResponse('Error: No access token received', status=400)

    user_data = requests.get(
        'https://api.spotify.com/v1/me',
        headers={'Authorization': f'Bearer {access_token}'}
    ).json()

    spotify_user_id = user_data.get('id')
    spotify_username = user_data.get('display_name')

    try:
        user = User.objects.get(username=spotify_user_id)
    except User.DoesNotExist:
        try:
            user = User.objects.create_user(
                username=spotify_user_id,
                password='random_password'
            )
        except IntegrityError:
            user = User.objects.create_user(
                username=spotify_user_id + str(random.randint(1, 1000)),
                password='random_password'
            )

    login(request, user)
    profile, created = Profile.objects.get_or_create(user=user)
    profile.spotify_access_token = access_token
    profile.save()

    wrapped_id = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
    SpotifyWrappedData.objects.create(
        user=profile,
        wrapped_id=wrapped_id,
        top_tracks=[],
        top_artists=[],
        top_genres=[],
        total_time_listened=0
    )

    return redirect('user_dashboard')

def refresh_token(request):
    refresh_token = request.session.get("refresh_token")
    token_url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET,
    }
    response = requests.post(token_url, data=data)
    token_info = response.json()
    request.session["access_token"] = token_info.get("access_token")


def user_dashboard(request):
    profile = Profile.objects.get(user=request.user)

    access_token = request.session.get("access_token")
    if access_token is None:
        return redirect("home")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Fetch data from Spotify API
    top_tracks = requests.get(
        "https://api.spotify.com/v1/me/top/tracks?limit=5", headers=headers
    ).json().get("items", [])

    top_artists = requests.get(
        "https://api.spotify.com/v1/me/top/artists?limit=5", headers=headers
    ).json().get("items", [])

    recent_tracks = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played?limit=50", headers=headers  # Use a larger limit if desired
    ).json().get("items", [])

    wrapped_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Calculate Top Genres
    genre_count = {}
    for artist in top_artists:
        for genre in artist.get("genres", []):
            genre_count[genre] = genre_count.get(genre, 0) + 1
    top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # Calculate Total Time Listened from recent tracks (in hours and minutes)
    total_time_ms = sum(track["track"]["duration_ms"] for track in recent_tracks)
    total_time_sec = total_time_ms / 1000  # convert ms to seconds
    total_time_min = total_time_sec / 60
    hours = int(total_time_min // 60)
    minutes = int(total_time_min % 60)
    total_time_listened = f"{hours} hrs {minutes} mins"

    # Prepare additional slides data
    top_track_popularity = [
        {
            "name": track["name"],
            "popularity": track["popularity"],
            "image": track["album"]["images"][0]["url"]
        }
        for track in top_tracks if track.get("album") and track["album"].get("images")
    ]

    artist_followers = [
        {
            "name": artist["name"],
            "followers": artist["followers"]["total"],
            "image": artist["images"][0]["url"]
        }
        for artist in top_artists if artist.get("images")
    ]

    # Organize data into slides
    slides = [
        {"title": "Welcome", "items": [], "content": "Welcome to Your Spotify Wrapped! Discover your top tracks, artists, and more!"},
        {"title": "Your top tracks", "items": top_tracks},
        {"title": "How popular are your favorite tunes?", "items": top_track_popularity},
        {"title": "The artists who kept you going", "items": top_artists},
        {"title": "Genres you loved", "items": top_genres},
        {"title": "Your recent mood", "items": recent_tracks},
        {"title": "Overall time Listened", "items": [], "content": total_time_listened},
        {"title": "Artist Followers", "items": artist_followers},
        {"title": "Thanks", "items": [], "content": "That's a wrap on your Spotify highlights!"}
    ]
    #store in database
    SpotifyWrappedData.objects.create(
        user=profile,
        wrapped_id=wrapped_id,
        top_tracks=top_tracks,
        top_artists=top_artists,
        top_genres=top_genres,
        total_time_listened=int(total_time_min),
    )
    context = {"slides": slides,
               'wrapped_id': wrapped_id}
    return render(request, "wrapped/dashboard.html", context)


def shareable_page(request, wrapped_id):
    try:
        wrapped_data = SpotifyWrappedData.objects.get(wrapped_id=wrapped_id)
    except SpotifyWrappedData.DoesNotExist:
        return render(request, "wrapped/not_found.html")  # Error page if ID is invalid

    context = {
        "top_tracks": wrapped_data.top_tracks,
        "top_artists": wrapped_data.top_artists,
        "top_genres": wrapped_data.top_genres,
        "total_time_listened": wrapped_data.total_time_listened,
    }
    return render(request, "wrapped/shareable.html", context)




