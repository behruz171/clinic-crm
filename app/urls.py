from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet, ClinicViewSet, RoleViewSet, SpecializationViewSet
from .charts import (
    ClinicUserChartView, RoleDistributionChartView, MonthlyRegistrationChartView,
    DailyActivityChartView, SpecializationStatsChartView, UserStatusChartView
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('clinics', ClinicViewSet)
router.register('roles', RoleViewSet, basename='role')
router.register('specializations', SpecializationViewSet, basename='specialization')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('charts/clinic-users/', ClinicUserChartView.as_view(), name='clinic_users_chart'),
    path('charts/role-distribution/', RoleDistributionChartView.as_view(), name='role_distribution_chart'),
    path('charts/monthly-registration/', MonthlyRegistrationChartView.as_view(), name='monthly_registration_chart'),
    path('charts/daily-activity/', DailyActivityChartView.as_view(), name='daily_activity_chart'),
    path('charts/specialization-stats/', SpecializationStatsChartView.as_view(), name='specialization_stats_chart'),
    path('charts/user-status/', UserStatusChartView.as_view(), name='user_status_chart'),
] 