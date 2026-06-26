from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("manage/", include("instruments.manager_urls")),
    path("", include("instruments.urls")),
]
