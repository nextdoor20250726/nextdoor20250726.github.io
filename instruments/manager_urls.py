from django.urls import path
from . import manager

urlpatterns = [
    path("", manager.manager_login, name="manager_login"),
    path("logout/", manager.manager_logout_view, name="manager_logout"),
    path("dashboard/", manager.manager_dashboard, name="manager_dashboard"),
    path("download-excel/", manager.download_excel, name="manager_download_excel"),
    path("upload-excel/", manager.upload_excel, name="manager_upload_excel"),
]
