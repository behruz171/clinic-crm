from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.shortcuts import render
from .models import *
from .charts import ClinicUserChartView, RoleDistributionChartView, MonthlyRegistrationChartView
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import logging
from django.template.loader import render_to_string
from . import signals
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'clinic','branch', 'status', 'is_active')
    list_filter = ('role', 'clinic', 'status', 'is_active')
    
    # UserAdmin fieldsets ni o'zgartiramiz
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'salary')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Additional Info', {'fields': ('role', 'clinic','branch', 'phone_number', 'specialization', 'status')}),
    )
    
    # Add form uchun fieldset
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2','email', 'clinic', 'role', 'phone_number', 'status'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Yangi foydalanuvchi qo'shishda
            form.base_fields['clinic'].required = True
            form.base_fields['role'].required = True
        return form

class ChartAdmin(admin.ModelAdmin):
    model = Statistics

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.charts_view), name='app_charts'),
        ]
        return custom_urls + urls

    def charts_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title="Statistika",
            # Umumiy statistika
            total_users=User.objects.count(),
            active_clinics=Clinic.objects.filter(is_active=True).count(),
            new_users_today=User.objects.filter(date_joined__date=timezone.now().date()).count(),
            active_users=User.objects.filter(is_active=True).count(),
        )
        return render(request, 'admin/charts.html', context)

    def has_module_permission(self, request):
        return True

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'license_number', 'email', 'is_active', 'created_at')  # Include email
    list_filter = ('is_active',)
    search_fields = ('name', 'license_number', 'phone_number', 'email')  # Include email
    ordering = ('name',)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title','message', 'created_at')
    # exclude = ('sent_by',)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Yangi notification yaratilganda
            # Barcha faol foydalanuvchilar emailini olish
            emails = User.objects.filter(is_active=True).values_list('email', flat=True)
            
            # HTML xabar tayyorlash
            html_message = render_to_string('email/notification.html', {
                'title': obj.title,
                'message': obj.message,
            })
            
            # HTML dan text versiyani olish
            plain_message = strip_tags(html_message)
            
            try:
                # Har bir emailga xabar yuborish
                for email in emails:
                    if email:  # Bo'sh bo'lmagan emaillar uchun
                        msg = EmailMultiAlternatives(
                            subject=obj.title,
                            body=plain_message,
                            from_email=settings.EMAIL_HOST_USER,
                            to=[email]
                        )
                        msg.attach_alternative(html_message, "text/html")
                        msg.send()
                        print(f"Email sent to {email}")
                
                messages.success(request, f"Xabar {len(emails)} ta foydalanuvchiga yuborildi")
            except Exception as e:
                messages.error(request, f"Xatolik yuz berdi: {str(e)}")
                print(f"Failed to send email: {e}")
            
        super().save_model(request, obj, form, change)


class ClinicNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'clinic', 'created_at')
    search_fields = ('title', 'clinic__name')
    ordering = ('-created_at',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:  # Faqat yangi clinic notification yaratilganda
            try:
                # HTML xabar tayyorlash
                html_message = render_to_string('email/clinic_notification.html', {
                    'title': obj.title,
                    'message': obj.message,
                    'clinic': obj.clinic.name,
                })
                
                # HTML dan text versiyani olish
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject=obj.title,
                    message=plain_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[obj.clinic.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                print(f"Email sent to {obj.clinic.email}")
            except Exception as e:
                print(f"Failed to send email: {e}")

admin.site.register(User, CustomUserAdmin)
admin.site.register(Clinic, ClinicAdmin)
admin.site.register(Branch)
admin.site.register(Cabinet)
admin.site.register(Customer)
admin.site.register(Meeting)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ClinicNotification, ClinicNotificationAdmin)
admin.site.register(UserNotification)
admin.site.register(Statistics, ChartAdmin)
admin.site.register(CashWithdrawal)