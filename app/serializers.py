from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *
from app2.models import *

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ('id', 'name', 'phone_number','email', 'license_number', 'is_active')
    
    def validate_email(self, value):
        if Clinic.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email bilan klinika allaqachon mavjud.")
        return value

class ClinicLogoSerializer(serializers.ModelSerializer):
    begin_contract = serializers.DateField(format='%Y.%m.%d', required=False)
    end_contract = serializers.DateField(format='%Y.%m.%d', required=False)
    class Meta:
        model = Clinic
        fields = ['id', 'name', 'logo', 'begin_contract', 'end_contract']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)  # Not required in the request
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    role_name = serializers.CharField(source='role', read_only=True)  # Adjusted to match the model
    specialization_name = serializers.CharField(source='specialization', read_only=True)

    class Meta:
        model = User
        fields = (  'id', 'email', 'password', 'first_name', 'last_name', 
                    'role', 'role_name', 'phone_number', 'specialization',
                    'specialization_name', 'status', 'clinic', 'branch', 'clinic_name',
                    'salary', 'kpi', 'reason_holiday', 'start_holiday', 'end_holiday')  # Removed 'username'
        # extra_kwargs = {
        #     'clinic': {'read_only': True},  # Automatically set from the authenticated user
        #     'branch': {'read_only': True},
        # }
    
    def create(self, validated_data):
        # Ensure username is set to email during creation
        validated_data['username'] = validated_data.get('email')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()  # Foydalanuvchi uchun o'qilganligini ko'rsatadi
    class Meta:
        model = Notification
        fields = '__all__'
        # read_only_fields = ('sent_by',)
    
    def get_is_read(self, obj):
        user = self.context['request'].user
        read_status = NotificationReadStatus.objects.filter(user=user, notification=obj).first()
        return read_status.is_read if read_status else False

class ClinicNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()  # Foydalanuvchi uchun o'qilganligini ko'rsatadi

    class Meta:
        model = ClinicNotification
        fields = ['id', 'title', 'message', 'created_at', 'clinic', 'branch', 'is_read']

    def get_is_read(self, obj):
            user = self.context['request'].user
            return ClinicNotificationReadStatus.objects.filter(user=user, clinic_notification=obj, is_read=True).exists()

class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = "__all__"

class CabinetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']

class CabinetSerializer(serializers.ModelSerializer):
    user_doctor = serializers.SerializerMethodField()
    user_nurse = serializers.SerializerMethodField()
    
    class Meta:
        model = Cabinet
        fields = '__all__'

    def get_user_doctor(self, obj):
        users = obj.user.filter(role='doctor')
        return CabinetUserSerializer(users, many=True).data

    def get_user_nurse(self, obj):
         # Filter nurses from the ManyToManyField 'nurse'
        nurses = obj.nurse.all()  # Use the 'nurse' field directly
        return CabinetUserSerializer(nurses, many=True).data

class CustomerSerializer(serializers.ModelSerializer):
    last_hospitalization_info = serializers.SerializerMethodField()  # Custom field for last hospitalization info
    class Meta:
        model = Customer
        fields = '__all__'
        extra_fields = ['last_hospitalization_info']  # Add the custom field
    
    def get_last_hospitalization_info(self, obj):
        """
        Retrieves the last hospitalization's doctor and diagnosis.
        """
        last_hospitalization = obj.hospitalizations.order_by('-start_date').first()
        if last_hospitalization:
            return {
                "doctor": last_hospitalization.doctor.get_full_name(),
                "diagnosis": last_hospitalization.diagnosis
            }
        return {
            "doctor": None,
            "diagnosis": None
        }


class MeetingFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingFile
        fields = ['id', 'file']
    
class DentalServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model = DentalService
        fields = [
            'id',
            'clinic',        # write_only: True qilishingiz mumkin, lekin ko‘pincha faqat o‘qish uchun kerak
            'clinic_name',   # faqat o‘qish uchun
            'category',
            'category_name', # faqat o‘qish uchun
            'name',
            'description',
            'amount',
            'teeth_number'
        ]
        read_only_fields = ['clinic', 'clinic_name', 'category_name']

class MeetingSerializer(serializers.ModelSerializer):
    branch_name = serializers.StringRelatedField(source='branch.name', read_only=True)  # Branch nomi
    customer_name = serializers.StringRelatedField(source='customer.full_name', read_only=True)  # Customer nomi
    customer_gender = serializers.StringRelatedField(source='customer.gender', read_only=True)
    doctor_name = serializers.StringRelatedField(source='doctor.first_name', read_only=True)  # Doctor nomi
    room_name = serializers.StringRelatedField(source='room.name', read_only=True)  # Room nomi
    date = serializers.SerializerMethodField(read_only=True)  # Faqat o'qish uchun
    time = serializers.SerializerMethodField(read_only=True)  # Faqat o'qish uchun
    full_date = serializers.DateTimeField(write_only=True, source='date')  # Faqat yozish uchun
    files = MeetingFileSerializer(many=True, read_only=True)  # Fayllarni ko'rish uchun
    uploaded_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )  # Fayllarni yuklash uchun
    dental_services_data = DentalServiceSerializer(source='dental_services', many=True, read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'branch', 'branch_name', 'customer', 'customer_name',
            'doctor', 'doctor_name', 'room','room_name', 'date', 'time', 'full_date', 'status',
            'organs', 'comment', 'dental_services', 'customer_gender', 'diognosis', 'files', 'uploaded_files',
            'dental_services_data'
        ]
        # extra_kwargs = {
        #     'branch': {'write_only': True},  # ID orqali yozish uchun
        #     'customer': {'write_only': True},  # ID orqali yozish uchun
        #     'doctor': {'write_only': True},  # ID orqali yozish uchun
        #     'room': {'write_only': True},  # ID orqali yozish uchun
        # }
    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        meeting = super().create(validated_data)

        # Fayllarni saqlash
        for file in uploaded_files:
            MeetingFile.objects.create(meeting=meeting, file=file)

        return meeting
    
    def update(self, instance, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        meeting = super().update(instance, validated_data)

        # Yangi fayllarni saqlash
        for file in uploaded_files:
            MeetingFile.objects.create(meeting=meeting, file=file)

        return meeting
    
    def get_date(self, obj):
        """
        Returns only the date part of the datetime.
        """
        return obj.date.date() if obj.date else None

    def get_time(self, obj):
        """
        Returns only the time part of the datetime.
        """
        return obj.date.time() if obj.date else None

class BranchSerializer(serializers.ModelSerializer):
    clinic = serializers.StringRelatedField(read_only=True)  # Include clinic as read-only

    class Meta:
        model = Branch
        fields = ['id', 'name', 'address', 'phone_number', 'email', 'clinic']  # Add 'clinic' to fields

class RoomSerializer(serializers.ModelSerializer):
    customers = serializers.PrimaryKeyRelatedField(many=True, queryset=Customer.objects.all())

    class Meta:
        model = Room
        fields = '__all__'

class CashWithdrawalSerializer(serializers.ModelSerializer):
    clinic = serializers.StringRelatedField(read_only=True)
    # branch = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CashWithdrawal
        fields = '__all__'

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'role']

class TaskSerializer(serializers.ModelSerializer):
    assignee_data = UserDetailSerializer(source='assignee', read_only=True)  # Include detailed assignee info
    created_by = UserDetailSerializer(read_only=True)  # Include detailed created_by info

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'start_date', 'start_time', 'end_date', 'end_time',
            'status', 'priority', 'assignee', 'assignee_data', 'created_by', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']




class DentalServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DentalServiceCategory
        fields = ['id', 'name']


class DentalServiceBulkCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    description = serializers.CharField(allow_blank=True, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.PrimaryKeyRelatedField(queryset=DentalServiceCategory.objects.all())

    def create(self, validated_data):
        clinic = self.context['request'].user.clinic
        services = []
        for i in range(1, 33):
            service = DentalService.objects.create(
                clinic=clinic,
                category=validated_data['category'],
                name=validated_data['name'],
                description=validated_data.get('description', ''),
                amount=validated_data['amount'],
                teeth_number=i
            )
            services.append(service)
        return services