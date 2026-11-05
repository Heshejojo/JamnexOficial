from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0005_merge_sim_transfer_and_device'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simtransferconflict',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pendiente'),
                    ('TRANSFERRED', 'Transferida'),
                    ('STALE', 'Desactualizada'),
                    ('DISMISSED', 'Conservada'),
                    ('ACKNOWLEDGED', 'Aviso visto'),
                ],
                default='PENDING',
                max_length=20,
            ),
        ),
    ]
