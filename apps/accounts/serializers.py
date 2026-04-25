from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from apps.accounts.models import User, PatientProfile, DoctorProfile, ReceptionistProfile, AdminProfile


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'phone', 'is_active', 'date_joined']
        read_only_fields = ['id', 'is_active', 'date_joined']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientProfile
        fields = [
            'id', 'user', 'user_id', 'date_of_birth', 'gender', 'address',
            'emergency_contact_name', 'emergency_contact_phone', 'age',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_age(self, obj):
        if obj.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - obj.date_of_birth.year - ((today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day))
        return None


class PatientProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(write_only=True)
    
    class Meta:
        model = PatientProfile
        fields = ['user', 'date_of_birth', 'gender', 'address', 'emergency_contact_name', 'emergency_contact_phone']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserCreateSerializer().create(user_data)
        patient_profile = PatientProfile.objects.create(user=user, **validated_data)
        return patient_profile


class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'user_id', 'specialization', 'license_number',
            'consultation_duration_minutes', 'buffer_before_minutes', 'buffer_after_minutes',
            'bio', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DoctorProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(write_only=True)
    
    class Meta:
        model = DoctorProfile
        fields = [
            'user', 'specialization', 'license_number',
            'consultation_duration_minutes', 'buffer_before_minutes', 'buffer_after_minutes', 'bio'
        ]
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserCreateSerializer().create(user_data)
        doctor_profile = DoctorProfile.objects.create(user=user, **validated_data)
        return doctor_profile


class ReceptionistProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ReceptionistProfile
        fields = ['id', 'user', 'user_id', 'employee_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReceptionistProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(write_only=True)
    
    class Meta:
        model = ReceptionistProfile
        fields = ['user', 'employee_code']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserCreateSerializer().create(user_data)
        receptionist_profile = ReceptionistProfile.objects.create(user=user, **validated_data)
        return receptionist_profile


class AdminProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = AdminProfile
        fields = ['id', 'user', 'user_id', 'employee_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdminProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer(write_only=True)
    
    class Meta:
        model = AdminProfile
        fields = ['user', 'employee_code']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserCreateSerializer().create(user_data)
        user.is_staff = True
        user.save()
        admin_profile = AdminProfile.objects.create(user=user, **validated_data)
        return admin_profile


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer to return appropriate profile based on user type"""
    profile_type = serializers.SerializerMethodField()
    profile_data = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'profile_type', 'profile_data']
    
    def get_profile_type(self, obj):
        if hasattr(obj, 'patient_profile'):
            return 'patient'
        elif hasattr(obj, 'doctor_profile'):
            return 'doctor'
        elif hasattr(obj, 'receptionist_profile'):
            return 'receptionist'
        elif hasattr(obj, 'admin_profile'):
            return 'admin'
        return 'unknown'
    
    def get_profile_data(self, obj):
        if hasattr(obj, 'patient_profile'):
            return PatientProfileSerializer(obj.patient_profile).data
        elif hasattr(obj, 'doctor_profile'):
            return DoctorProfileSerializer(obj.doctor_profile).data
        elif hasattr(obj, 'receptionist_profile'):
            return ReceptionistProfileSerializer(obj.receptionist_profile).data
        elif hasattr(obj, 'admin_profile'):
            return AdminProfileSerializer(obj.admin_profile).data
        return None
