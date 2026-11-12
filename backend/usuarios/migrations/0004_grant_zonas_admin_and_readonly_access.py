from django.db import migrations


MODULE_PERMISSION_KEYS = ('dashboard', 'dispositivos', 'sims', 'usuarios', 'zonas')


def update_existing_permissions(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'Usuario')

    for user in Usuario.objects.select_related('rol').all().iterator():
        role_name = user.rol.nombre.upper() if user.rol else ''
        if role_name not in {'ADMIN', 'CONSULTA'}:
            continue

        permisos = user.permisos if isinstance(user.permisos, dict) else {}
        if role_name == 'ADMIN':
            permisos.setdefault('zonas', True)
        else:
            permisos.update({key: True for key in MODULE_PERMISSION_KEYS})
        Usuario.objects.filter(pk=user.pk).update(permisos=permisos)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_consulta_role'),
    ]

    operations = [
        migrations.RunPython(update_existing_permissions, migrations.RunPython.noop),
    ]
