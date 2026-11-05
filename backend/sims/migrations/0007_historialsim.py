import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispositivos', '0003_dispositivo_sim_report_status'),
        ('sims', '0006_simtransferconflict_acknowledged'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistorialSim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slot', models.IntegerField(blank=True, null=True)),
                ('desde', models.DateTimeField(auto_now_add=True)),
                ('hasta', models.DateTimeField(blank=True, null=True)),
                ('consumo_mb', models.FloatField(default=0)),
                ('ultimo_reporte', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('dispositivo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historial_sims', to='dispositivos.dispositivo')),
                ('sim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historial', to='sims.sim')),
            ],
            options={
                'ordering': ['-desde'],
            },
        ),
    ]
