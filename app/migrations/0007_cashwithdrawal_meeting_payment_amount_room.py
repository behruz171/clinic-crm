# Generated by Django 5.1.7 on 2025-03-26 08:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_user_salary_cabinet_customer_meeting'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashWithdrawal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('reason', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='meeting',
            name='payment_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('type', models.CharField(choices=[('standard', 'Standard Room'), ('deluxe', 'Deluxe Room'), ('vip', 'VIP Room')], default='standard', max_length=50)),
                ('floor', models.CharField(choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='1', max_length=10)),
                ('capacity', models.PositiveIntegerField(default=1)),
                ('daily_price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('available', 'Available'), ('occupied', 'Occupied'), ('maintenance', 'Maintenance')], default='available', max_length=20)),
                ('description', models.TextField()),
                ('customers', models.ManyToManyField(blank=True, related_name='rooms', to='app.customer')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
