from django.db import migrations


def create_consulta_role(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Rol.objects.get_or_create(
        nombre='CONSULTA',
        defaults={
            'descripcion': 'Puede consultar los módulos permitidos sin modificarlos.',
            'activo': True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_usuario_permisos'),
    ]

    operations = [
        migrations.RunPython(create_consulta_role, migrations.RunPython.noop),
    ]
