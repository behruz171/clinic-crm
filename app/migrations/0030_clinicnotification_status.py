# Generated by Django 5.1.7 on 2025-05-06 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0029_clinicnotification_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicnotification',
            name='status',
            field=models.CharField(choices=[('doctor', 'Doctor'), ('admin', 'Admin'), ('director', 'Director'), ('admin_director', 'Admin and Director')], default='admin_director', max_length=20),
        ),
    ]
