from django.db import models
from app.models import *

class SubscriptionPlan(models.Model):
    PLAN_CHOICES = (
        ('Basic', 'Basic'),
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
        ('Enterprise', 'Enterprise'),
        ('Trial', 'Trial'),
    )

    name = models.CharField(max_length=50, choices=PLAN_CHOICES)
    storage_limit_gb = models.DecimalField(max_digits=5, decimal_places=2)  # GB
    discount = models.CharField(max_length=50, null=True, blank=True)  # Masalan, "10% for annual payment"
    trial_period_days = models.IntegerField(null=True, blank=True)  # Sinov muddati (kunlarda)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Narx (so'mda)

    def __str__(self):
        return self.name


class ClinicSubscription(models.Model):
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.clinic.name} - {self.plan.name}"


class ApiIssue(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Tekshirilmoqda'),
        ('in_progress', 'Jarayonda'),
        ('resolved', 'Hal qilingan'),
    )

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='api_issues')
    api_name = models.CharField(max_length=255)
    issue_description = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    affected_users = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.clinic.name} - {self.api_name} ({self.get_status_display()})"