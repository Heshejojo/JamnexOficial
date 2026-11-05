from django.db import migrations


def normalize_existing_iccids(apps, schema_editor):
    Sim = apps.get_model('sims', 'Sim')
    for sim in Sim.objects.only('pk', 'iccid').iterator():
        normalized = ''.join(
            character for character in str(sim.iccid or '').upper() if character.isalnum()
        )
        if normalized.startswith('S') and normalized[1:].isdigit():
            normalized = normalized[1:]
        normalized = normalized.rstrip('F')
        if normalized.isdigit() and len(normalized) == 20:
            normalized = normalized[:19]
        if sim.iccid_normalized != normalized:
            Sim.objects.filter(pk=sim.pk).update(iccid_normalized=normalized)


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0004_sim_dispositivo'),
        ('sims', '0004_simtransferconflict_dismissed'),
    ]

    operations = [
        migrations.RunPython(normalize_existing_iccids, migrations.RunPython.noop),
    ]
