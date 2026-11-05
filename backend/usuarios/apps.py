import sys

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_demo_user(sender, **kwargs):
    if sender.name != 'usuarios' or 'test' in sys.argv:
        return

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not User.objects.filter(
        username='admin',
    ).exists() and not User.objects.filter(email='admin@agente.cfe').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@agente.cfe',
            password='Admin123!',
            first_name='Admin',
            last_name='CFE',
            is_staff=True,
        )


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'
