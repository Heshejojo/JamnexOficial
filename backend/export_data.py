"""
Exporta los datos actuales de la base (SQLite en local) a data.json,
forzando UTF-8 para evitar problemas de codificación en Windows.
Correr con: python export_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

with open('data.json', 'w', encoding='utf-8') as f:
    call_command(
        'dumpdata',
        natural_foreign=True,
        natural_primary=True,
        exclude=['contenttypes', 'auth.permission', 'admin.logentry', 'sessions.session'],
        indent=2,
        stdout=f,
    )

print("Listo: data.json generado en UTF-8.")