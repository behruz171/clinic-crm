from rest_framework import serializers
from .models import *

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id','name', 'storage_limit_gb', 'trial_period_days', 'price', 'description']


class ClinicSubscriptionSerializer(serializers.ModelSerializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.all())  # ForeignKey uchun PrimaryKey ishlatiladi

    class Meta:
        model = ClinicSubscription
        fields = ['plan', 'clinic', 'start_date', 'end_date', 'discount', 'description_discount']

class ApiIssueSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model = ApiIssue
        fields = ['id', 'clinic', 'clinic_name', 'api_name', 'issue_description', 'reported_at', 'resolved_at', 'affected_users', 'status']


class ApiIssueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiIssue
        fields = ['status', 'resolved_at']


class ClinicSubscriptionHistorySerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = ClinicSubscriptionHistory
        fields = ['id', 'clinic', 'clinic_name', 'plan', 'plan_name', 'start_date', 'end_date', 'price', 'discount', 'paid_amount', 'status']