from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispositivos', '0002_credencialdispositivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='dispositivo',
            name='sim_count_reported',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dispositivo',
            name='sims_reported_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
