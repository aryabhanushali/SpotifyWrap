import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.contrib import messages
from urllib.parse import urlencode
import datetime
import random
import string
from .models import SpotifyWrappedData, Profile
from django.utils import timezone
from functools import wraps


def check_theme(request):
    """Get current theme or set default to system preference"""
    return request.session.get('theme', 'light')


def check_spotify_token(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        access_token = request.session.get("access_token")
        if not access_token:
            messages.warning(request, "Please log in with Spotify to continue.")
            return redirect("home")

        try:
            response = requests.get(
                "https://api.spotify.com/v1/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 401:
                refresh_token(request)
        except requests.RequestException:
            messages.error(request, "Error connecting to Spotify. Please try again.")
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def home(request):
    context = {
        'theme': check_theme(request),
        'page_title': 'Home',
    }
    return render(request, "wrapped/home.html", context)


def spotify_login(request):
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "show_dialog": "true",
        "scope": "user-top-read user-read-recently-played user-read-private",
    }
    url = f"{auth_url}?{urlencode(params)}"
    return redirect(url)


def spotify_logout(request):
    for key in ['access_token', 'refresh_token']:
        request.session.pop(key, None)
    messages.success(request, "Successfully logged out!")
    return redirect("home")


def spotify_callback(request):
    try:
        code = request.GET.get("code")
        if not code:
            messages.error(request, "Authorization failed. Please try again.")
            return redirect("home")

        token_url = "https://accounts.spotify.com/api/token"
        response = requests.post(
            token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
            }
        )
        response.raise_for_status()
        token_info = response.json()

        request.session["access_token"] = token_info["access_token"]
        request.session["refresh_token"] = token_info["refresh_token"]
        request.session["token_expiry"] = (
                timezone.now() + datetime.timedelta(seconds=token_info["expires_in"])
        ).isoformat()

        return redirect("user_dashboard")

    except requests.RequestException as e:
        messages.error(request, "Failed to connect to Spotify. Please try again.")
        return redirect("home")


def refresh_token(request):
    try:
        refresh_token = request.session.get("refresh_token")
        if not refresh_token:
            return False

        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
            }
        )
        response.raise_for_status()
        token_info = response.json()

        request.session["access_token"] = token_info["access_token"]
        request.session["token_expiry"] = (
                timezone.now() + datetime.timedelta(seconds=token_info["expires_in"])
        ).isoformat()

        if "refresh_token" in token_info:
            request.session["refresh_token"] = token_info["refresh_token"]

        return True
    except requests.RequestException:
        for key in ['access_token', 'refresh_token', 'token_expiry']:
            request.session.pop(key, None)
        return False


@check_spotify_token
def user_dashboard(request):
    try:
        headers = {"Authorization": f"Bearer {request.session['access_token']}"}

        def fetch_spotify_data(url):
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        # Fetch all required data
        top_tracks = fetch_spotify_data(
            "https://api.spotify.com/v1/me/top/tracks?limit=5"
        ).get("items", [])

        top_artists_response = fetch_spotify_data(
            "https://api.spotify.com/v1/me/top/artists?limit=5"
        ).get("items", [])

        # Process artist data
        top_artists = []
        for artist in top_artists_response:
            artist_tracks = fetch_spotify_data(
                f"https://api.spotify.com/v1/artists/{artist['id']}/top-tracks?market=US"
            ).get("tracks", [])[:5]

            recent_tracks = fetch_spotify_data(
                "https://api.spotify.com/v1/me/player/recently-played?limit=50"
            ).get("items", [])

            artist_time_ms = sum(
                track["track"]["duration_ms"]
                for track in recent_tracks
                if any(a["id"] == artist["id"] for a in track["track"]["artists"])
            )

            artist_minutes = artist_time_ms / (1000 * 60)
            artist.update({
                "top_tracks": artist_tracks,
                "listening_time": {
                    "hours": int(artist_minutes // 60),
                    "minutes": int(artist_minutes % 60),
                    "total_ms": artist_time_ms
                }
            })
            top_artists.append(artist)

        wrapped_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Calculate Top Genres
        genre_count = {}
        for artist in top_artists:
            for genre in artist.get("genres", []):
                genre_count[genre] = genre_count.get(genre, 0) + 1
        top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:5]

        # Calculate Total Time Listened
        total_time_ms = sum(track["track"]["duration_ms"] for track in recent_tracks)
        total_time_min = total_time_ms / (1000 * 60)
        hours = int(total_time_min // 60)
        minutes = int(total_time_min % 60)
        total_time_listened = f"{hours} hrs {minutes} mins"

        # Prepare slides data
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
                "items": top_artists,
                "artist_details": True
            },
            {
                "title": "Top Genres",
                "items": top_genres
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

        # Save to database
        try:
            SpotifyWrappedData.objects.create(
                user=request.user.profile,
                wrapped_id=wrapped_id,
                top_tracks=top_tracks,
                top_artists=top_artists,
                top_genres=dict(top_genres),
                total_time_listened=int(total_time_min)
            )
        except Exception as e:
            messages.warning(request, "Your data was fetched but couldn't be saved for sharing.")

        context = {
            "slides": slides,
            "wrapped_id": wrapped_id,
            "theme": check_theme(request),
            "page_title": "Your Wrapped"
        }
        return render(request, "wrapped/dashboard.html", context)

    except requests.RequestException as e:
        messages.error(request, "Failed to fetch your Spotify data. Please try again.")
        return redirect("home")


def shareable_page(request, wrapped_id):
    try:
        wrapped_data = SpotifyWrappedData.objects.get(wrapped_id=wrapped_id)
        context = {
            "top_tracks": wrapped_data.top_tracks,
            "top_artists": wrapped_data.top_artists,
            "top_genres": wrapped_data.top_genres,
            "total_time_listened": wrapped_data.total_time_listened,
            "theme": check_theme(request),
            "page_title": "Shared Wrapped"
        }
        return render(request, "wrapped/shareable.html", context)
    except SpotifyWrappedData.DoesNotExist:
        return render(request, "wrapped/not_found.html", {
            "theme": check_theme(request),
            "page_title": "Not Found"
        })


def toggle_theme(request):
    """Toggle between light and dark themes"""
    current_theme = request.session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    request.session['theme'] = new_theme
    return JsonResponse({
        'status': 'success',
        'theme': new_theme
    })


def error_404(request, exception):
    """Custom 404 page"""
    return render(request, 'wrapped/404.html', {
        'theme': check_theme(request),
        'page_title': 'Page Not Found'
    }, status=404)


def error_500(request):
    """Custom 500 page"""
    return render(request, 'wrapped/500.html', {
        'theme': check_theme(request),
        'page_title': 'Server Error'
    }, status=500)