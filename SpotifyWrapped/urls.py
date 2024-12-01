"""
URL configuration for SpotifyWrapped project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from wrapped import views


urlpatterns = [
    path("", views.home, name="home"),
    path("spotify/login/", views.spotify_login, name="spotify_login"),
    path("spotify/callback/", views.spotify_callback, name="spotify_callback"),
    path("dashboard/", views.user_dashboard, name="user_dashboard"),
    path("spotify/logout/", views.spotify_logout, name="spotify_logout"),
    path('wrapped/<str:wrapped_id>/', views.shareable_page, name='shareable_page'),
    path("old_wrappeds/", views.view_old_wrappeds, name="old_wrappeds"),
    path("contact_devs/", views.contact_devs, name="contact_devs"),
    path('download-wrapped-image/', views.download_wrapped_image, name='download_wrapped_image'),
]
