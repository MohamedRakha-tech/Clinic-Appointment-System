import factory
from factory.django import DjangoModelFactory
from uuid import uuid4

from django.contrib.auth import get_user_model

from accounts.models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile


User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    role_name = None
    username = factory.LazyFunction(lambda: f"user_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = factory.Faker("msisdn")
    is_active = True
    is_staff = False
    password = factory.PostGenerationMethodCall("set_password", "Password123!")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        role_name = kwargs.pop("role_name", None) or cls.role_name
        kwargs.pop("_target_role", None)
        password = kwargs.pop("password", "Password123!")
        obj = model_class(*args, **kwargs)
        if role_name:
            obj._target_role = role_name
        obj.set_password(password)
        obj.save()
        return obj


class PatientUserFactory(UserFactory):
    role_name = "patient"
    username = factory.LazyFunction(lambda: f"patient_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class DoctorUserFactory(UserFactory):
    role_name = "doctor"
    username = factory.LazyFunction(lambda: f"doctor_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class ReceptionistUserFactory(UserFactory):
    role_name = "receptionist"
    username = factory.LazyFunction(lambda: f"reception_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    is_staff = True


class AdminUserFactory(UserFactory):
    role_name = "admin"
    username = factory.LazyFunction(lambda: f"admin_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    is_staff = True


class PatientProfileFactory(DjangoModelFactory):
    class Meta:
        model = PatientProfile

    user = factory.SubFactory(PatientUserFactory)
    date_of_birth = factory.Faker("date_of_birth", minimum_age=18, maximum_age=90)
    gender = factory.Iterator(["Male", "Female"])
    address = factory.Faker("address")
    emergency_contact_name = factory.Faker("name")
    emergency_contact_phone = factory.Faker("msisdn")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.pop("user")
        defaults = {
            "date_of_birth": kwargs.pop("date_of_birth", None),
            "gender": kwargs.pop("gender", None),
            "address": kwargs.pop("address", None),
            "emergency_contact_name": kwargs.pop("emergency_contact_name", None),
            "emergency_contact_phone": kwargs.pop("emergency_contact_phone", None),
        }
        profile, _ = model_class.objects.update_or_create(user=user, defaults=defaults)
        return profile


class DoctorProfileFactory(DjangoModelFactory):
    class Meta:
        model = DoctorProfile

    user = factory.SubFactory(DoctorUserFactory)
    specialization = factory.Iterator(
        [
            "Cardiology",
            "Dermatology",
            "Neurology",
            "Pediatrics",
            "Orthopedics",
            "Internal Medicine",
        ]
    )
    license_number = factory.LazyFunction(lambda: f"LIC-{uuid4().hex[:12].upper()}")
    consultation_duration_minutes = factory.Iterator([10, 15, 20, 30])
    buffer_before_minutes = factory.Iterator([0, 5, 10])
    buffer_after_minutes = factory.Iterator([0, 5, 10])
    bio = factory.Faker("paragraph", nb_sentences=3)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.pop("user")
        defaults = {
            "specialization": kwargs.pop("specialization", "General Medicine"),
            "license_number": kwargs.pop("license_number", f"LIC-{uuid4().hex[:12].upper()}"),
            "consultation_duration_minutes": kwargs.pop("consultation_duration_minutes", 15),
            "buffer_before_minutes": kwargs.pop("buffer_before_minutes", 5),
            "buffer_after_minutes": kwargs.pop("buffer_after_minutes", 5),
            "bio": kwargs.pop("bio", None),
        }
        profile, _ = model_class.objects.update_or_create(user=user, defaults=defaults)
        return profile


class ReceptionistProfileFactory(DjangoModelFactory):
    class Meta:
        model = ReceptionistProfile

    user = factory.SubFactory(ReceptionistUserFactory)
    employee_code = factory.LazyFunction(lambda: f"REC-{uuid4().hex[:10].upper()}")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.pop("user")
        defaults = {
            "employee_code": kwargs.pop("employee_code", f"REC-{uuid4().hex[:10].upper()}"),
        }
        profile, _ = model_class.objects.update_or_create(user=user, defaults=defaults)
        return profile


class AdminProfileFactory(DjangoModelFactory):
    class Meta:
        model = AdminProfile

    user = factory.SubFactory(AdminUserFactory)
    employee_code = factory.LazyFunction(lambda: f"ADM-{uuid4().hex[:10].upper()}")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.pop("user")
        defaults = {
            "employee_code": kwargs.pop("employee_code", f"ADM-{uuid4().hex[:10].upper()}"),
        }
        profile, _ = model_class.objects.update_or_create(user=user, defaults=defaults)
        return profile
