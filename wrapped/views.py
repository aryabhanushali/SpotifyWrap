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
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django import forms
from .models import SpotifyWrappedData

def user_dashboard(request):

    """
    Render the user dashboard with Spotify Wrapped data.

    This view fetches the user's Spotify Wrapped data, including their top tracks,
    artists, genres, and total listening time, and prepares it for display on a
    multi-slide UI.

    Args:
        request (HttpRequest): The HTTP request object, which may contain GET
                               parameters for time range filters.

    Returns:
        HttpResponse: A response object rendering the user dashboard template.
    """
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
from django.http import FileResponse
from PIL import Image, ImageDraw, ImageFont
import io


def download_wrapped_image(request):
    """
    Generate and return a downloadable image with Spotify Wrapped data.

    This function fetches the user's top tracks and artists from Spotify's API
    and generates a personalized image using the PIL library.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        FileResponse: A downloadable image response in PNG format.
        JsonResponse: Error response if the user is not authenticated or access token is missing.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    access_token = request.session.get("access_token")
    if not access_token:
        refresh_token(request)
        access_token = request.session.get("access_token")
    if access_token is None:
        return JsonResponse({'error': 'No access token'}, status=400)

    headers = {"Authorization": f"Bearer {access_token}"}

    # Fetch top tracks
    top_tracks = requests.get(
        "https://api.spotify.com/v1/me/top/tracks?limit=5",
        headers=headers
    ).json().get("items", [])

    # Fetch top artists
    top_artists = requests.get(
        "https://api.spotify.com/v1/me/top/artists?limit=5",
        headers=headers
    ).json().get("items", [])

    img = Image.new('RGB', (400, 800), color='black')
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    d.text((20, 20), "Your Spotify Wrapped", fill='white', font=font)

    # Top Tracks
    d.text((20, 60), "Top Tracks:", fill='white', font=font)
    y_offset = 100
    for i, track in enumerate(top_tracks, 1):
        d.text((20, y_offset), f"{i}. {track['name']} - {track['artists'][0]['name']}", fill='white', font=font)
        y_offset += 30

    # Top Artists with listening time
    d.text((20, y_offset + 20), "Top Artists:", fill='white', font=font)
    y_offset += 60
    for i, artist in enumerate(top_artists, 1):
        # Simulate listening time (replace with actual data if available)
        listening_time = random.randint(1, 100)
        d.text((20, y_offset), f"{i}. {artist['name']} - {listening_time} hours", fill='white', font=font)
        y_offset += 30

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='spotify_wrapped.png')


# Create your views here.
def home(request):
    """
    Render the home page of the application.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A response object rendering the home template.
    """
    return render(request, "wrapped/home.html")

def spotify_login(request):
    """
    Redirect the user to the Spotify authorization page.

    This function constructs the Spotify OAuth2 authorization URL with the required
    parameters, including client ID, redirect URI, and scope. Once constructed, it
    redirects the user to Spotify's authorization page to allow access.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponseRedirect: A redirect response to Spotify's authorization URL.
    """
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "show_dialog": "true",
        "scope": "user-top-read user-read-recently-played",
    }
    url = f"{auth_url}?{urlencode(params)}"
    return redirect(url)


def spotify_logout(request):
    """
    Log the user out of the application.

    This function clears the user's session data, including the Spotify access token,
    and redirects them to the home page. It ensures no residual data is left after logout.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponseRedirect: A redirect response to the home page.
    """
    request.session.flush()  # Clears all session data
    print("Session after logout:", request.session.get("access_token"))
    return redirect("home")


def spotify_callback(request):
    """
    Handle Spotify OAuth2 callback and user authentication.

    This function processes the authorization code received from Spotify,
    exchanges it for an access token and refresh token, and retrieves user
    data from Spotify's API. It creates or updates a user profile in the database
    and logs the user into the application.

    Args:
        request (HttpRequest): The HTTP request object containing the Spotify
                               authorization code.

    Returns:
        HttpResponseRedirect: Redirects the user to the dashboard on success.
                              Returns an error response in case of failure.
    """
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
        total_time_listened=0
    )

    # Redirect to the user dashboard
    return redirect('user_dashboard')



def refresh_token(request):
    """
    Refresh Spotify API access token using the refresh token.

    This function retrieves the refresh token from the user's session and sends
    a request to Spotify's token endpoint to obtain a new access token. The new
    access token is stored back in the user's session for continued API access.

    Args:
        request (HttpRequest): The HTTP request object containing the user's session.

    Returns:
        None: Updates the session with the new access token.
    """
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
    """
    Render the user's Spotify Wrapped dashboard with personalized data.

    This view retrieves and processes Spotify API data, including top tracks, artists,
    genres, and listening history for the authenticated user. It organizes the data
    into slides for a rich user experience.

    Args:
        request (HttpRequest): The HTTP request object containing user session
                               and optional query parameters for time range.

    Returns:
        HttpResponse: Renders the dashboard template with the user's Spotify data.
        JsonResponse: Returns JSON data for slides if the request is made via AJAX.

    Raises:
        Http404: If the user's profile cannot be found.
        Redirect: Redirects unauthenticated users to the login page.
    """
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

    duration = request.GET.get('duration', 'long_term')

    # Fetch data from Spotify API
    top_tracks = requests.get(
        f"https://api.spotify.com/v1/me/top/tracks?limit=5&time_range={duration}", headers=headers
    ).json().get("items", [])

    # Fetch top artists with their detailed data
    top_artists_response = requests.get(
        f"https://api.spotify.com/v1/me/top/artists?limit=5&time_range={duration}", headers=headers
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
    # Calculate Total Time Listened
    total_time_ms = 0
    for track in recent_tracks:
        try:
            total_time_ms += track.get("track", {}).get("duration_ms", 0)
        except Exception as e:
            print(f"Error processing track: {e}")

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
            "title": "Total Time Listened to Recent Tracks ",
            "items": [],
            "content": total_time_listened
        },
        {
            "items": [],
            "content": "That's a wrap on your Spotify highlights!"
        }
    ]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"slides": slides})

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
               'duration': duration,
               }
    # started = request.GET.get('started') == 'true'
    # if started:
    #     return render(request, "wrapped/dashboard.html", context)
    # else:
    #     return render(request, "wrapped/home.html", context)
    return render(request, "wrapped/dashboard.html", context)

def shareable_page(request, wrapped_id):
    """
    Render a shareable page displaying the user's Spotify Wrapped data.

    This view retrieves Spotify Wrapped data based on the provided wrapped ID and
    renders a shareable page. If the wrapped ID is invalid, the user is redirected
    to the home page.

    Args:
        request (HttpRequest): The HTTP request object.
        wrapped_id (str): A unique identifier for the Spotify Wrapped data.

    Returns:
        HttpResponse: A response object rendering the shareable Wrapped page or
                      redirecting to the home page if the wrapped ID is invalid.
    """
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
    """
    Render a list of past Spotify Wrapped summaries for the logged-in user.

    This view fetches all past Spotify Wrapped summaries for the authenticated
    user and organizes them in reverse chronological order for display.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A response object rendering the page with past Wrapped summaries.
    """
    profile = Profile.objects.get(user=request.user)
    past_wrapped_summaries = SpotifyWrappedData.objects.filter(user=profile).order_by('-created_at')

    context = {
        "past_wrapped_summaries": past_wrapped_summaries,
    }
    return render(request, "wrapped/old_wrappeds.html", context)
class SaveWrapsForm(forms.Form):
    """
    Form for saving a custom name for a Spotify Wrapped summary.

    Fields:
        custom_name (CharField): A text field allowing the user to enter a custom name
                                 for their Wrapped summary, with a maximum length of 255 characters.
    """
    custom_name = forms.CharField(max_length=255, label="Name your wrap!")

def contact_devs(request):
    """
    Render a contact page listing the developers of the Spotify Wrapped application.

    This view provides contact information for the team members who worked on the
    application.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A response object rendering the developer contact page.
    """


    developers = [
        {"name": "Arsheya Gourav", "email": "arsheya.gourav29@gmail.con"},
        {"name": "Sruthi Medepalli", "email": "sruthi.medepalli@gmail.com"},
        {"name": "Arya Bhanushali", "email": "aryabhanush@gmail.com"},
        {"name": "Mihika Gottimukala", "email": "mihikacg@gmail.com"},
        {"name": "Ritish Pokhrel", "email": "ritish.pokhrel24@gmail.com"},
    ]
    return render(request, "wrapped/contact_devs.html", {'developers': developers})
