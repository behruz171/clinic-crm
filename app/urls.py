from django.urls import path, include
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *
from app2.views import *
from .charts import (
    ClinicUserChartView, RoleDistributionChartView, MonthlyRegistrationChartView,
    DailyActivityChartView, SpecializationStatsChartView, UserStatusChartView
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('clinics', ClinicViewSet, basename='clinics')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('user-notifications', UserNotificationViewSet, basename='user-notifications')
router.register('cabinets', CabinetViewSet, basename='cabinets')
router.register('customers', CustomerViewSet, basename='customers')
router.register('meetings', MeetingViewSet, basename='meetings')
router.register('branches', BranchViewSet, basename='branchs')
router.register('rooms', RoomViewSet, basename='rooms')
router.register('cash-withdrawals', CashWithdrawalViewSet, basename='cash-withdrawals')
router.register('tasks', TaskViewSet, basename='tasks')
router.register('vital-signs', VitalSignViewSet)
router.register('medicines', MedicineViewSet, basename='medicines')
router.register('medicine-schedules', MedicineScheduleViewSet, basename='medicine-schedules')
router.register('medicine-history', MedicineHistoryViewSet, basename='medicine-history')
router.register('user-schedules', NurseScheduleViewSet, basename='user-schedules')
router.register('hospitalizations', HospitalizationViewSet, basename='hospitalization')
router.register(r'faqs', FAQViewSet, basename='faq')
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
    path('signup/', SignupView.as_view(), name='signup'),
    path('get-notifications/', get_notifications, name='get_notifications'),
    path('html/', notifications_view),
    path('html2/', clinic_notifications_view),
    path('html3/', notification_global_view),
    path('user-statistics/', UserStatisticsView.as_view(), name='user_statistics'),
    path('cabinet-statistics/', CabinetStatisticsView.as_view(), name='cabinet_statistics'),
    path('export-customers-excel/', ExportCustomersExcelView.as_view(), name='export_customers_excel'),
    path('export-customers-pdf/', ExportCustomersPDFView.as_view(), name='export_customers_pdf'),
    path('filial/<str:branch_id>/financial-report/', FinancialReportView.as_view(), name='financial_report'),
    path('filial/<str:branch_id>/patient-statistics/', PatientStatisticsView.as_view(), name='patient_statistics'),
    path('filial/<str:branch_id>/doctor-statistics/', DoctorStatisticsView.as_view(), name='doctor_statistics'),
    # path('index/', notifications_view, name='notifications'),
    path('filial/<str:branch_id>/dashboard/financial-metrics/', FinancialMetricsView.as_view(), name='financial_metrics'),
    path('filial/<str:branch_id>/dashboard/doctor-efficiency/', DoctorEfficiencyView.as_view(), name='doctor_efficiency'),
    path('filial/<str:branch_id>/dashboard/customers-by-department/', CustomersByDepartmentView.as_view(), name='customers_by_department'),
    path('filial/<str:branch_id>/dashboard/monthly-customer-dynamics/', MonthlyCustomerDynamicsView.as_view(), name='monthly_customer_dynamics'),
    path('filial/<str:branch_id>/dashboard/department-efficiency/', DepartmentEfficiencyView.as_view(), name='department_efficiency'),
    path('filial/<str:branch_id>/dashboard/todays-appointments/', TodaysAppointmentsView.as_view(), name='todays_appointments'),
    path('dashboard/new-staff/', NewStaffView.as_view(), name='new_staff'),
    path('clinic/logo/', ClinicLogoView.as_view(), name='clinic_logo'),
    path('rooms/<int:room_id>/history/', RoomHistoryView.as_view(), name='room_history'),
    path('meetings-filter/', MeetingFilterView.as_view(), name='meeting_filter'),
]


#DepartmentEfficiencyView bu api ni topib urlga qoshib qoy .