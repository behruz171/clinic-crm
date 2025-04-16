from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ('id', 'name', 'phone_number', 'license_number', 'is_active')

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
                    'salary', 'reason_holiday', 'start_holiday', 'end_holiday')  # Removed 'username'
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
    class Meta:
        model = Notification
        fields = '__all__'
        # read_only_fields = ('sent_by',)

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

class MeetingSerializer(serializers.ModelSerializer):
    branch_name = serializers.StringRelatedField(source='branch.name', read_only=True)  # Branch nomi
    customer_name = serializers.StringRelatedField(source='customer.full_name', read_only=True)  # Customer nomi
    customer_gender = serializers.StringRelatedField(source='customer.gender', read_only=True)
    doctor_name = serializers.StringRelatedField(source='doctor.first_name', read_only=True)  # Doctor nomi
    room_name = serializers.StringRelatedField(source='room.name', read_only=True)  # Room nomi
    class Meta:
        model = Meeting
        fields = [
            'id', 'branch', 'branch_name', 'customer', 'customer_name',
            'doctor', 'doctor_name', 'room','room_name', 'date', 'status',
            'organs', 'comment', 'payment_amount', 'customer_gender'
        ]
        # extra_kwargs = {
        #     'branch': {'write_only': True},  # ID orqali yozish uchun
        #     'customer': {'write_only': True},  # ID orqali yozish uchun
        #     'doctor': {'write_only': True},  # ID orqali yozish uchun
        #     'room': {'write_only': True},  # ID orqali yozish uchun
        # }

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
    assignee = UserDetailSerializer(read_only=True)  # Include detailed assignee info
    created_by = UserDetailSerializer(read_only=True)  # Include detailed created_by info

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'start_date', 'start_time', 'end_date', 'end_time',
            'status', 'priority', 'assignee', 'created_by', 'created_at'
        ]
        read_only_fields = ['created_by', 'created_at']