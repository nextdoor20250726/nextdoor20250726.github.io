"""
Management command to create the manager user (soundweavers).
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create manager user: soundweavers"

    def handle(self, *args, **options):
        if User.objects.filter(username="soundweavers").exists():
            user = User.objects.get(username="soundweavers")
            user.set_password("soundweavers5201314")
            user.save()
            self.stdout.write("User soundweavers already exists — password updated.")
        else:
            User.objects.create_user(
                username="soundweavers",
                password="soundweavers5201314",
                is_staff=False,
                is_superuser=False,
            )
            self.stdout.write("User soundweavers created.")
