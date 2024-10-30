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
    print(access_token)
    if access_token == None:
        return redirect("home")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Fetch top tracks
    top_tracks_response = requests.get(
        "https://api.spotify.com/v1/me/top/tracks?limit=10", headers=headers
    )
    if top_tracks_response.status_code != 200:
        print(f"Top Tracks API Error: {top_tracks_response.status_code}")
        print(top_tracks_response.text)

    top_tracks = top_tracks_response.json().get("items", [])

    # Fetch top artists
    top_artists_response = requests.get(
        "https://api.spotify.com/v1/me/top/artists?limit=10", headers=headers
    )

    if top_artists_response.status_code != 200:
        print(f"Top Artists API Error: {top_artists_response.status_code}")
        print(top_artists_response.text)
    top_artists = top_artists_response.json().get("items", [])

    context = {"top_tracks": top_tracks, "top_artists": top_artists}
    return render(request, "wrapped/dashboard.html", context)
