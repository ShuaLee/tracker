"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Mounted at settings.ADMIN_URL rather than a literal "admin/" so a real
    # deployment can move it off the default path (DJANGO_ADMIN_URL env var).
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("holdings.urls")),
]
