from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0003_sim_iccid_normalized'),
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
                ],
                default='PENDING',
                max_length=20,
            ),
        ),
    ]
