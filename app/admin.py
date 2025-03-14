from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.shortcuts import render
from .models import User, Clinic, Role, Specialization, Statistics, Notification
from .charts import ClinicUserChartView, RoleDistributionChartView, MonthlyRegistrationChartView
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'clinic', 'status', 'is_active')
    list_filter = ('role', 'clinic', 'status', 'is_active')
    
    # UserAdmin fieldsets ni o'zgartiramiz
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Additional Info', {'fields': ('role', 'clinic', 'phone_number', 'specialization', 'status')}),
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

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'clinic', 'is_active', 'created_at')
    list_filter = ('clinic', 'is_active')
    search_fields = ('name', 'clinic__name')
    ordering = ('clinic', 'name')

class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'clinic', 'is_active', 'created_at')
    list_filter = ('clinic', 'is_active')
    search_fields = ('name', 'clinic__name')
    ordering = ('clinic', 'name')

class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'license_number', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'license_number', 'phone_number')
    ordering = ('name',)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'sent_by')
    exclude = ('sent_by',)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Yangi notification yaratilganda
            obj.sent_by = request.user
            
            # Barcha faol foydalanuvchilar emailini olish
            emails = User.objects.filter(is_active=True).values_list('email', flat=True)
            
            # HTML xabar tayyorlash
            html_message = render_to_string('email/notification.html', {
                'title': obj.title,
                'message': obj.message,
                'sender': request.user.get_full_name() or request.user.username
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
                
                messages.success(request, f"Xabar {len(emails)} ta foydalanuvchiga yuborildi")
            except Exception as e:
                messages.error(request, f"Xatolik yuz berdi: {str(e)}")
            
        super().save_model(request, obj, form, change)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Clinic, ClinicAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Specialization, SpecializationAdmin)
admin.site.register(Statistics, ChartAdmin)
admin.site.register(Notification, NotificationAdmin)
