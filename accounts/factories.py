from itertools import count
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile


User = get_user_model()

_user_seq = count(1)


def _unique_username(prefix):
    idx = next(_user_seq)
    return f"{prefix}{idx}"


def UserFactory(**kwargs):
    idx = next(_user_seq)
    username = kwargs.pop("username", f"user{idx}")
    email = kwargs.pop("email", f"{username}@example.com")
    password = kwargs.pop("password", "testpass123")
    return User.objects.create_user(username=username, email=email, password=password, **kwargs)


def PatientProfileFactory(**kwargs):
    user = kwargs.pop("user", None) or UserFactory()
    return PatientProfile.objects.create(user=user, **kwargs)


def DoctorProfileFactory(**kwargs):
    user = kwargs.pop("user", None) or UserFactory(username=_unique_username("doctor"))
    kwargs.setdefault("specialization", "General Medicine")
    kwargs.setdefault("license_number", f"LIC-{next(_user_seq)}")
    return DoctorProfile.objects.create(user=user, **kwargs)


def ReceptionistProfileFactory(**kwargs):
    user = kwargs.pop("user", None) or UserFactory(username=_unique_username("receptionist"))
    kwargs.setdefault("employee_code", f"REC-{next(_user_seq)}")
    return ReceptionistProfile.objects.create(user=user, **kwargs)


def AdminProfileFactory(**kwargs):
    user = kwargs.pop("user", None) or UserFactory(username=_unique_username("admin"), is_staff=True)
    kwargs.setdefault("employee_code", f"ADM-{next(_user_seq)}")
    return AdminProfile.objects.create(user=user, **kwargs)
