from django.db import models
from app.models import *

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)  # Qo'shimcha izohlar
    storage_limit_gb = models.DecimalField(max_digits=5, decimal_places=2)  # GB
    trial_period_days = models.IntegerField(null=True, blank=True)  # Sinov muddati (kunlarda)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Narx (so'mda)

    def __str__(self):
        return self.name


class ClinicSubscription(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    discount = models.CharField(max_length=50, null=True, blank=True)  # Masalan, "10% for annual payment"
    start_date = models.DateField()
    end_date = models.DateField()
    description_discount = models.TextField(null=True, blank=True)  # Qo'shimcha izohlar
    status = models.CharField(max_length=20, choices=(('active', 'Faol'), ('expired', 'Tugagan')), default='active')
    def __str__(self):
        return f"{self.clinic.name} - {self.plan.name} - {self.discount}"


class ApiIssue(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Tekshirilmoqda'),
        ('in_progress', 'Jarayonda'),
        ('resolved', 'Hal qilingan'),
    )

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='api_issues', null=True, blank=True)
    api_name = models.CharField(max_length=255)
    issue_description = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    affected_users = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # IP manzil uchun
    location = models.CharField(max_length=255, null=True, blank=True)
    def __str__(self):
        return f"{self.api_name} ({self.get_status_display()})"


class ClinicSubscriptionHistory(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='subscription_history')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Narx (so'mda)
    discount = models.CharField(max_length=50, null=True, blank=True)  # Masalan, "10% for annual payment"
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # To'langan summa
    status = models.CharField(max_length=20, choices=(('active', 'Faol'), ('expired', 'Tugagan')), default='active')

    def __str__(self):
        return f"{self.clinic.name} - {self.plan.name} ({self.status})"