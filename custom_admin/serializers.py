from rest_framework import serializers
from .models import *

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id','name', 'storage_limit_gb', 'discount', 'trial_period_days', 'price']


class ClinicSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer()

    class Meta:
        model = ClinicSubscription
        fields = ['plan', 'start_date', 'end_date']

class ApiIssueSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model = ApiIssue
        fields = ['id', 'clinic', 'clinic_name', 'api_name', 'issue_description', 'reported_at', 'resolved_at', 'affected_users', 'status']


class ApiIssueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiIssue
        fields = ['status', 'resolved_at']