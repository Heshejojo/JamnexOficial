from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consumos', '0002_consumosyncstate'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='consumosyncstate',
            name='unique_consumption_sync_device_date',
        ),
        migrations.AddConstraint(
            model_name='consumosyncstate',
            constraint=models.UniqueConstraint(
                fields=('dispositivo', 'fecha', 'sim'),
                name='unique_consumption_sync_device_date_sim',
            ),
        ),
    ]
