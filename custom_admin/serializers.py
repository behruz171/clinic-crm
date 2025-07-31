from rest_framework import serializers
from .models import *

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id','name', 'storage_limit_gb', 'trial_period_days', 'price', 'description']


class ClinicSubscriptionSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2, read_only=True)
    class Meta:
        model = ClinicSubscription
        fields = [
            'id', 'clinic', 'clinic_name', 'plan', 'plan_name', 
            'start_date', 'end_date', 'price', 'discount', 
            'description_discount', 'status', 'paid_amount'
        ]

class ApiIssueSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model = ApiIssue
        fields = ['id', 'clinic', 'clinic_name', 'api_name', 'issue_description', 'reported_at', 'resolved_at', 'affected_users', 'status']


class ApiIssueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiIssue
        fields = ['status', 'resolved_at']


class InactiveClinicSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    clinic_email = serializers.CharField(source='clinic.email', read_only=True)

    class Meta:
        model = InactiveClinic
        fields = ['id', 'clinic', 'clinic_name', 'clinic_email', 'since', 'inactive_days', 'notified', 'comment']

class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = [
            'id', 'name', 'phone_number', 'location', 'clinic_name',
            'comment', 'status'
        ]