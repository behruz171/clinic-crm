from django.contrib import admin
from .models import *  # Custom admin interfeysini import qilish
admin.site.register(SubscriptionPlan)
admin.site.register(ClinicSubscription)
admin.site.register(ApiIssue)