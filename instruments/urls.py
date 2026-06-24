from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("instruments/", views.instrument_list, name="instrument_list"),
    path("categories/<slug:slug>/", views.category_detail, name="instrument_category"),
    path("instruments/<int:pk>/", views.instrument_detail, name="instrument_detail"),
]
