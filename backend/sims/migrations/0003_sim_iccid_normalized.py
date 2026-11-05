from django.db import migrations, models


def normalize_existing_iccids(apps, schema_editor):
    Sim = apps.get_model('sims', 'Sim')
    for sim in Sim.objects.only('pk', 'iccid').iterator():
        normalized = ''.join(
            character for character in str(sim.iccid or '').upper() if character.isalnum()
        )
        if normalized.startswith('S') and normalized[1:].isdigit():
            normalized = normalized[1:]
        if sim.iccid_normalized != normalized:
            Sim.objects.filter(pk=sim.pk).update(iccid_normalized=normalized)


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0002_simtransferconflict'),
    ]

    operations = [
        migrations.AddField(
            model_name='sim',
            name='iccid_normalized',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.RunPython(normalize_existing_iccids, migrations.RunPython.noop),
    ]
