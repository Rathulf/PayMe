import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER')
        email = os.environ.get('DJANGO_SUPERUSER')
        password = os.environ.get('DJANGO_SUPERPASS')
        if not all([username, email, password]):
            self.stdout.write("Superuser enc vars incomplete; skipped")
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            self.stdout.write("Superuser created successfully")
        else:
            self.stdout.write("Superuser already exists")

