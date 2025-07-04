from django.urls import path, include
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *
from custom_admin.views import *
from app2.views import *
from .charts import (
    ClinicUserChartView, RoleDistributionChartView, MonthlyRegistrationChartView,
    DailyActivityChartView, SpecializationStatsChartView, UserStatusChartView
)

router = DefaultRouter()
router.register(r'contact-requests', ContactRequestViewSet, basename='contact-request')
router.register('users', UserViewSet, basename='users')
router.register('clinics', ClinicViewSet, basename='clinics')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('clinic-notifications', ClinicNotificationViewSet, basename='clinic-notification')
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
router.register(r'dental-services', DentalServiceViewSet, basename='dental-services')
router.register(r'dental-service-categories', DentalServiceCategoryViewSet, basename='dental-service-category')


urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Charts URLs
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

    path('filial/<str:branch_id>/financial-report/export/pdf/', FinancialReportExportPDFView.as_view(), name='financial_report_export_pdf'),
    path('filial/<str:branch_id>/patient-statistics/export/pdf/', PatientStatisticsExportPDFView.as_view(), name='patient_statistics_export_pdf'),
    path('filial/<str:branch_id>/doctor-statistics/export/pdf/', DoctorStatisticsExportPDFView.as_view(), name='doctor_statistics_export_pdf'),

    path('filial/<str:branch_id>/today-stats/', TodayStatsView.as_view(), name='today_stats'),
    path('clinic/tariff-stats/', ClinicTariffStatsView.as_view(), name='clinic_tariff_stats'),

    # Dashboard URLs
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
    path('meeting-public/<int:clinic_id>/<int:meeting_id>/', MeetingPublicView.as_view(), name='meeting_public'),
    # Reset password URLs
    path('user/change-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('user/verify-code/', PasswordResetCodeVerifyView.as_view(), name='password-reset-code-verify'),
    path('user/reset-password/', PasswordResetChangeView.as_view(), name='password-reset-change'),

    # Read notification URL
    path('notification/mark-as-read/', MarkNotificationAsReadView.as_view(), name='mark_notification_as_read'),
    path('clinic-notification/mark-as-read/', MarkClinicNotificationAsReadView.as_view(), name='mark_clinic_notification_as_read'),
    path('notification/mark-all-as-read/', MarkAllNotificationsAsReadView.as_view(), name='mark_all_notifications_as_read'),
    path('clinic-notification/mark-all-as-read/', MarkAllClinicNotificationsAsReadView.as_view(), name='mark_all_clinic_notifications_as_read'),
    path('notification/unread-count/', UnreadNotificationCountView.as_view(), name='unread_notification_count'),
    path('clinic-notification/unread-count/', UnreadClinicNotificationCountView.as_view(), name='unread_clinic_notification_count'),


    # ADMIN Dashboard URLs
    path('filial/<str:branch_id>/dashboard/metrics/', DashboardMetricsView.as_view(), name='dashboard_metrics'),
    path('filial/<str:branch_id>/dashboard/weekly-appointments/', WeeklyAppointmentsView.as_view(), name='weekly_appointments'),
    path('filial/<str:branch_id>/dashboard/patient-distribution/', PatientDistributionView.as_view(), name='patient_distribution'),
    path('filial/<str:branch_id>/dashboard/monthly-customer-trend/', MonthlyCustomerTrendView.as_view(), name='monthly_customer_trend'),
    path('filial/<str:branch_id>/dashboard/recent-patients/', RecentPatientsView.as_view(), name='recent_patients'),
    path('filial/<str:branch_id>/dashboard/pending-tasks/', PendingTasksView.as_view(), name='pending_tasks'),
    path('filial/<str:branch_id>/dashboard/cabinet-utilization/', CabinetUtilizationView.as_view(), name='cabinet_utilization'),


    # DOCTOR Dashboard URLs
    path('doctor/dashboard/', DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('doctor/dashboard/todays-appointments/', DoctorAppointmentsView.as_view(), name='doctor_todays_appointments'),
    path('doctor/dashboard/patient-trend/', DoctorPatientTrendView.as_view(), name='doctor_patient_trend'),
    path('doctor/dashboard/weekly-tasks/', DoctorWeeklyTasksView.as_view(), name='doctor_weekly_tasks'),
    path('doctor/dashboard/monthly-meetings-status/', DoctorMonthlyMeetingsStatusView.as_view(), name='doctor_monthly_meetings_status'),
    path('doctor/dashboard/weekly-customers/', DoctorWeeklyCustomersView.as_view(), name='doctor_weekly_customers'),


    path('dental-service/bulk-create/', DentalServiceBulkCreateView.as_view(), name='dental_service_bulk_create'),
    path('dental-service/name-summary/', DentalServiceNameSummaryView.as_view(), name='dental_service_name_summary'),
    path('dental-service/by-name/<int:service_id>/', DentalServiceByNameView.as_view(), name='dental_service_by_name'),
    path('dental-service/bulk-update/<int:service_id>/', DentalServiceBulkUpdateByNameView.as_view(), name='dental_service_bulk_update_by_name'),
]