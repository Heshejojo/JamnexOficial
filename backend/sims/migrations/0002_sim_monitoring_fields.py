from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sims', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sim',
            name='carrier_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sim',
            name='esim',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sim',
            name='tecnologia',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='sim',
            name='roaming',
            field=models.BooleanField(default=False),
        ),
    ]
