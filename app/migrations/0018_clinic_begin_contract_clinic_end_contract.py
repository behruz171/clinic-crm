# Generated by Django 5.1.7 on 2025-04-12 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0017_room_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinic',
            name='begin_contract',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='clinic',
            name='end_contract',
            field=models.DateField(blank=True, null=True),
        ),
    ]
