from rest_framework import serializers
from .models import User, Clinic, Role, Specialization

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ('id', 'name', 'address', 'phone_number', 'license_number', 'is_active')

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'is_active')

    def create(self, validated_data):
        # Avtomatik clinic qo'shish
        validated_data['clinic'] = self.context['request'].user.clinic
        return super().create(validated_data)

class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ('id', 'name', 'is_active')

    def create(self, validated_data):
        # Avtomatik clinic qo'shish
        validated_data['clinic'] = self.context['request'].user.clinic
        return super().create(validated_data)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    specialization_name = serializers.CharField(source='specialization.name', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 
                 'email', 'role', 'role_name', 'phone_number', 'specialization',
                 'specialization_name', 'status', 'clinic', 'clinic_name')
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True) 