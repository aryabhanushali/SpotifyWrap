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
from django.urls import reverse
import datetime
from django.shortcuts import get_object_or_404
from django import forms
from .models import SpotifyWrappedData


def user_dashboard(request):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return redirect('login')

    # Retrieve the Profile object associated with the current user
    profile = get_object_or_404(Profile, user=request.user)

    # Now you can use `profile` to render dashboard data or pass it to the template
    context = {
        'spotify_access_token': profile.spotify_access_token,
        # Add any other data you want to show on the dashboard
    }

    return render(request, 'dashboard.html', context)

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
        "scope": "user-top-read",
    }
    url = f"{auth_url}?{urlencode(params)}"
    return redirect(url)


def spotify_logout(request):
    request.session.flush()  # Clears all session data
    print("Session after logout:", request.session.get("access_token"))
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

    # Check for response errors
    if response.status_code != 200:
        return HttpResponse(f"Error: {response.json().get('error_description', 'Unknown error')}", status=400)
    # Parse the JSON response to get the access token
    data = response.json()
    access_token = data.get('access_token')

    if not access_token:
        return HttpResponse('Error: No access token received', status=400)

    request.session['access_token'] = access_token
    request.session['refresh_token'] = data.get('refresh_token')

    # Request user data from Spotify using the access token
    user_data = requests.get(
        'https://api.spotify.com/v1/me',
        headers={'Authorization': f'Bearer {access_token}'}
    ).json()

    if not user_data.get('id'):
        return HttpResponse('Error: Unable to fetch user data from Spotify', status=400)

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

    # Log the user in
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
        total_time_listened=0,
        custom_name=request.POST.get('custom_name', '')
    )

    # Redirect to the user dashboard
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
    if not request.user.is_authenticated:
        return redirect('login')

    profile = get_object_or_404(Profile, user=request.user)

    access_token = request.session.get("access_token")
    if not access_token:
        refresh_token(request)
        access_token = request.session.get("access_token")

    if access_token is None:
        return redirect("home")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Fetch data from Spotify API
    top_tracks = requests.get(
        "https://api.spotify.com/v1/me/top/tracks?limit=5", headers=headers
    ).json().get("items", [])

    # Fetch top artists with their detailed data
    top_artists_response = requests.get(
        "https://api.spotify.com/v1/me/top/artists?limit=5", headers=headers
    ).json().get("items", [])

    # Enhance artist data with their top tracks
    top_artists = []
    for artist in top_artists_response:
        # Get artist's top tracks
        artist_tracks = requests.get(
            f"https://api.spotify.com/v1/artists/{artist['id']}/top-tracks?market=US",
            headers=headers
        ).json().get("tracks", [])[:5]  # Limit to top 5 tracks

        # Get recent tracks to calculate listening time for this artist
        recent_tracks = requests.get(
            "https://api.spotify.com/v1/me/player/recently-played?limit=50",
            headers=headers
        ).json().get("items", [])

        # Calculate time spent on this artist
        artist_time_ms = sum(
            track["track"]["duration_ms"]
            for track in recent_tracks
            if any(a["id"] == artist["id"] for a in track["track"]["artists"])
        )

        # Convert to hours and minutes
        artist_minutes = artist_time_ms / (1000 * 60)
        artist_hours = int(artist_minutes // 60)
        artist_mins = int(artist_minutes % 60)

        # Add enhanced data to artist object
        artist.update({
            "top_tracks": artist_tracks,
            "listening_time": {
                "hours": artist_hours,
                "minutes": artist_mins,
                "total_ms": artist_time_ms
            }
        })
        top_artists.append(artist)

    # Rest of your existing code for recent tracks and genres
    recent_tracks = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played?limit=50",
        headers=headers
    ).json().get("items", [])

    wrapped_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Calculate Top Genres
    genre_count = {}
    for artist in top_artists:
        for genre in artist.get("genres", []):
            genre_count[genre] = genre_count.get(genre, 0) + 1

    top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # Calculate Total Time Listened
    total_time_ms = sum(track["track"]["duration_ms"] for track in recent_tracks)
    total_time_sec = total_time_ms / 1000
    total_time_min = total_time_sec / 60
    hours = int(total_time_min // 60)
    minutes = int(total_time_min % 60)
    total_time_listened = f"{hours} hrs {minutes} mins"

    # Prepare additional slides data
    top_track_popularity = [
        {
            "name": track["name"],
            "popularity": track["popularity"],
            "image": track["album"]["images"][0]["url"],
            "preview_url": track.get("preview_url"),  # Added preview URL for audio playback
            "artists": track["artists"]
        }
        for track in top_tracks if track.get("album") and track["album"].get("images")
    ]

    artist_followers = [
        {
            "name": artist["name"],
            "followers": artist["followers"]["total"],
            "image": artist["images"][0]["url"],
            "genres": artist.get("genres", []),
            "popularity": artist.get("popularity", 0),
            "top_tracks": artist["top_tracks"],
            "listening_time": artist["listening_time"]
        }
        for artist in top_artists if artist.get("images")
    ]

    # Organize data into slides with enhanced artist data
    slides = [
        {
            "title": "Welcome",
            "items": [],
            "content": "Welcome to Your Spotify Wrapped! Discover your top tracks, artists, and more!"
        },
        {
            "title": "Top Tracks",
            "items": top_tracks
        },
        {
            "title": "Top Artists",
            "items": top_artists,  # Now includes top_tracks and listening_time
            "artist_details": True  # Flag to indicate this slide has detailed artist data
        },
        {
            "title": "Recently Played",
            "items": recent_tracks
        },
        {
            "title": "Top Genres",
            "items": top_genres
        },
        {
            "title": "Track Popularity",
            "items": top_track_popularity
        },
        {
            "title": "Artist Followers",
            "items": artist_followers
        },
        {
            "title": "Total Time Listened",
            "items": [],
            "content": total_time_listened
        },
        {
            "title": "Thanks",
            "items": [],
            "content": "That's a wrap on your Spotify highlights!"
        }
    ]
    shareable_page_url = reverse('shareable_page', kwargs={'wrapped_id': wrapped_id})
    if request.method == "POST":
        form = SaveWrapsForm(request.POST)
        if form.is_valid():
            custom_name = form.cleaned_data["custom_name"]
            SpotifyWrappedData.objects.create(
                user=profile,
                wrapped_id=wrapped_id,
                top_tracks=top_tracks,
                top_artists=top_artists,
                top_genres=top_genres,
                total_time_listened=int(total_time_min),
                custom_name=custom_name,
            )
            return redirect('shareable_page', wrapped_id=wrapped_id)
    else:
        form = SaveWrapsForm()
    context = {"slides": slides,
               'wrapped_id': wrapped_id,
               'shareable_page_url': shareable_page_url,
               }
    started = request.GET.get('started') == 'true'
    if started:
        return render(request, "wrapped/dashboard.html", context)
    else:
        return render(request, "wrapped/home.html", context)


def shareable_page(request, wrapped_id):
    try:
        wrapped_data = SpotifyWrappedData.objects.get(wrapped_id=wrapped_id)
    except SpotifyWrappedData.DoesNotExist:
        return render(request, "home")  # Error page if ID is invalid

    context = {
        "top_tracks": wrapped_data.top_tracks,
        "top_artists": wrapped_data.top_artists,
        "top_genres": wrapped_data.top_genres,
        "total_time_listened": wrapped_data.total_time_listened,
    }
    return render(request, "wrapped/shareable.html", context)

def view_old_wrappeds(request):
    profile = Profile.objects.get(user=request.user)
    past_wrapped_summaries = SpotifyWrappedData.objects.filter(user=profile).order_by('-created_at')

    context = {
        "past_wrapped_summaries": past_wrapped_summaries,
    }
    return render(request, "wrapped/old_wrappeds.html", context)

class SaveWrapsForm(forms.Form):
    custom_name = forms.CharField(max_length=255, label="Name your wrap!")