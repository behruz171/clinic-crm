from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register(r'clinic-subscription-history', ClinicSubscriptionHistoryViewSet, basename='clinic-subscription-history')
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'clinic-subscriptions', ClinicSubscriptionViewSet, basename='clinic-subscription')
router.register(r'api-issues', ApiIssueViewSet, basename='api-issue')
router.register(r'inactive-clinics', InactiveClinicViewSet)
router.register(r'targets', TargetViewSet, basename='target')

urlpatterns = router.urls

urlpatterns += [
    path("clinics/", ClinicListView.as_view(), name="clinic_list"),
    path('clinics/<int:clinic_id>/notify/', ClinicNotifyView.as_view()),
    path('clinics/<int:clinic_id>/', ClinicDetailView.as_view(), name='clinic_detail'),
    path('clinics/<int:clinic_id>/branches/', BranchListView.as_view(), name='branch_list'),
    path('clinics/<int:clinic_id>/subscription/', SubscriptionDetailView.as_view(), name='subscription_detail'),
    path('clinics/<int:clinic_id>/financial/', FinancialDetailView.as_view(), name='financial_detail'),
    path('clinics/<int:clinic_id>/branches/statistics/', BranchStatisticsView.as_view(), name='branch_statistics'),
    path('login/', SuperuserLoginView.as_view(), name='superuser_login'),
    path('clinics/select/', ClinicSelectListView.as_view(), name='clinic_select_list'),
    path('subscription-plan/select/', SubscriptionPlanSelectListView.as_view(), name='subscription_plan_select_list'),
    path('clinic/<int:clinic_id>/subscription-history/', ClinicSubscriptionHistoryInIDView.as_view(), name='clinic_subscription_history'),

    path('targets/stats/', TargetStatsView.as_view()),
]