from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.leagues.urls")),
    path("api/", include("apps.matches.urls")),
    path("api/", include("apps.predictions.urls")),
    path("admin/", admin.site.urls),
]
