import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consumos', '0001_initial'),
        ('dispositivos', '0002_credencialdispositivo'),
        ('sims', '0006_simtransferconflict_acknowledged'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumoSyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('ultimo_acumulado_mb', models.FloatField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('dispositivo', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consumo_sync_states',
                    to='dispositivos.dispositivo',
                )),
                ('sim', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='consumo_sync_states',
                    to='sims.sim',
                )),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('dispositivo', 'fecha'),
                        name='unique_consumption_sync_device_date',
                    ),
                ],
            },
        ),
    ]
