# Generated by Django 5.1.7 on 2025-03-27 14:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_cashwithdrawal_branch_cashwithdrawal_clinic'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clinic',
            name='address',
        ),
    ]
