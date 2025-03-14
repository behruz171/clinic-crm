from chartjs.views.base import JSONView
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDate, ExtractHour
from .models import User, Clinic, Role, Specialization
from django.utils import timezone
from datetime import timedelta
from random import randint

class ChartJSONView(JSONView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["labels"] = self.get_labels()
        context["datasets"] = self.get_datasets()
        return context

class ClinicUserChartView(ChartJSONView):
    def get_labels(self):
        return list(Clinic.objects.values_list('name', flat=True))

    def get_datasets(self):
        clinics = Clinic.objects.all()
        counts = [User.objects.filter(clinic=clinic).count() for clinic in clinics]
        return [{
            'label': 'Foydalanuvchilar soni',
            'data': counts,
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            'borderColor': 'rgba(75, 192, 192, 1)',
            'borderWidth': 1
        }]

class RoleDistributionChartView(ChartJSONView):
    def get_labels(self):
        return list(Role.objects.values_list('name', flat=True))

    def get_datasets(self):
        roles = Role.objects.all()
        counts = [User.objects.filter(role=role).count() for role in roles]
        return [{
            'data': counts,
            'backgroundColor': [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)'
            ],
            'borderColor': [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)'
            ],
            'borderWidth': 1
        }]

class MonthlyRegistrationChartView(ChartJSONView):
    def get_labels(self):
        monthly_data = (
            User.objects.annotate(month=TruncMonth('date_joined'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        return [data['month'].strftime('%Y-%m') for data in monthly_data]

    def get_datasets(self):
        monthly_data = (
            User.objects.annotate(month=TruncMonth('date_joined'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        return [{
            'label': "Ro'yxatdan o'tganlar",
            'data': [data['count'] for data in monthly_data],
            'fill': False,
            'borderColor': 'rgb(75, 192, 192)',
            'tension': 0.1
        }]

class DailyActivityChartView(ChartJSONView):
    def get_labels(self):
        dates = []
        today = timezone.now().date()
        for i in range(7):
            dates.append((today - timedelta(days=i)).strftime('%Y-%m-%d'))
        return dates[::-1]

    def get_datasets(self):
        dates = self.get_labels()
        counts = []
        for date in dates:
            count = User.objects.filter(last_login__date=date).count()
            counts.append(count)
        return [{
            'label': 'Faol foydalanuvchilar',
            'data': counts,
            'fill': True,
            'borderColor': 'rgb(54, 162, 235)',
            'backgroundColor': 'rgba(54, 162, 235, 0.2)',
            'tension': 0.1
        }]

class SpecializationStatsChartView(ChartJSONView):
    def get_labels(self):
        return list(Specialization.objects.filter(is_active=True).values_list('name', flat=True))

    def get_datasets(self):
        specializations = Specialization.objects.filter(is_active=True)
        
        counts = []
        labels = []
        colors = []
        
        for spec in specializations:
            user_count = User.objects.filter(specialization=spec, is_active=True).count()
            if user_count > 0:
                counts.append(user_count)
                labels.append(f"{spec.name} ({user_count})")
                colors.append(f'rgba({randint(0,255)}, {randint(0,255)}, {randint(0,255)}, 0.2)')
        
        return [{
            'label': 'Mutaxassisliklar',
            'data': counts,
            'backgroundColor': colors,
            'borderColor': [color.replace('0.2', '1') for color in colors],
            'borderWidth': 1
        }]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not context['datasets'][0]['data']:
            context['labels'] = ['Ma\'lumot yo\'q']
            context['datasets'][0]['data'] = [0]
            context['datasets'][0]['backgroundColor'] = ['rgba(200, 200, 200, 0.2)']
            context['datasets'][0]['borderColor'] = ['rgba(200, 200, 200, 1)']
        return context

class UserStatusChartView(ChartJSONView):
    def get_labels(self):
        return ['Faol', 'Nofaol', "Ta'tilda"]

    def get_datasets(self):
        active = User.objects.filter(status='faol').count()
        inactive = User.objects.filter(status='nofaol').count()
        vacation = User.objects.filter(status='tatilda').count()
        return [{
            'data': [active, inactive, vacation],
            'backgroundColor': [
                'rgba(46, 204, 113, 0.2)',
                'rgba(231, 76, 60, 0.2)',
                'rgba(241, 196, 15, 0.2)'
            ],
            'borderColor': [
                'rgba(46, 204, 113, 1)',
                'rgba(231, 76, 60, 1)',
                'rgba(241, 196, 15, 1)'
            ],
            'borderWidth': 1
        }] 