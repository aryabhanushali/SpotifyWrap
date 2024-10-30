import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import JsonResponse
from urllib.parse import urlencode


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
    code = request.GET.get("code")
    token_url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET,
    }
    response = requests.post(token_url, headers=headers, data=data)
    token_info = response.json()

    # Save tokens in session
    request.session["access_token"] = token_info.get("access_token")
    request.session["refresh_token"] = token_info.get("refresh_token")
    return redirect("user_dashboard")


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
        "https://api.spotify.com/v1/me/player/recently-played?limit=5", headers=headers
    ).json().get("items", [])

    # Process data for additional slides
    top_genres = {}
    for artist in top_artists:
        for genre in artist.get("genres", []):
            top_genres[genre] = top_genres.get(genre, 0) + 1
    top_genres = sorted(top_genres.items(), key=lambda x: x[1], reverse=True)[:5]

    top_track_popularity = [{"name": track["name"], "popularity": track["popularity"]} for track in top_tracks]

    artist_followers = [{"name": artist["name"], "followers": artist["followers"]["total"]} for artist in top_artists]

    # Organize data into slides
    slides = [
        {"title": "Top Tracks", "items": top_tracks},
        {"title": "Top Artists", "items": top_artists},
        {"title": "Recently Played", "items": recent_tracks},
        {"title": "Top Genres", "items": top_genres},
        {"title": "Track Popularity", "items": top_track_popularity},
        {"title": "Artist Followers", "items": artist_followers},
    ]

    context = {"slides": slides}
    return render(request, "wrapped/dashboard.html", context)


