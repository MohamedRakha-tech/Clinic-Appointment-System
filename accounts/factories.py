from uuid import uuid4

import factory
from factory.django import DjangoModelFactory

from .models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile, User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(lambda: f"user_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = factory.Faker("msisdn")
    is_active = True
    is_staff = False
    password = factory.PostGenerationMethodCall("set_password", "Password123!")


class PatientUserFactory(UserFactory):
    username = factory.LazyFunction(lambda: f"patient_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class DoctorUserFactory(UserFactory):
    username = factory.LazyFunction(lambda: f"doctor_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class ReceptionistUserFactory(UserFactory):
    username = factory.LazyFunction(lambda: f"reception_{uuid4().hex[:12]}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    is_staff = True


class AdminUserFactory(UserFactory):
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


class ReceptionistProfileFactory(DjangoModelFactory):
    class Meta:
        model = ReceptionistProfile

    user = factory.SubFactory(ReceptionistUserFactory)
    employee_code = factory.LazyFunction(lambda: f"REC-{uuid4().hex[:10].upper()}")


class AdminProfileFactory(DjangoModelFactory):
    class Meta:
        model = AdminProfile

    user = factory.SubFactory(AdminUserFactory)
    employee_code = factory.LazyFunction(lambda: f"ADM-{uuid4().hex[:10].upper()}")
