import django.db.models.deletion
import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispositivos', '0001_initial'),
        ('sims', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SimTransferConflict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('TRANSFERRED', 'Transferida'), ('STALE', 'Desactualizada')], default='PENDING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('sim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_conflicts', to='sims.sim')),
                ('source_device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='outgoing_sim_transfer_conflicts', to='dispositivos.dispositivo')),
                ('target_device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='incoming_sim_transfer_conflicts', to='dispositivos.dispositivo')),
            ],
        ),
        migrations.AddConstraint(
            model_name='simtransferconflict',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'PENDING')), fields=('sim', 'target_device'), name='unique_pending_sim_transfer_target'),
        ),
    ]
