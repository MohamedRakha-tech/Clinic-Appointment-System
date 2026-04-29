import factory
from factory.django import DjangoModelFactory

from appointments.factories import AppointmentFactory
from appointments.models import Appointment
from .models import ConsultationRecord, PrescriptionItem, RequestedTest


class ConsultationRecordFactory(DjangoModelFactory):
    class Meta:
        model = ConsultationRecord

    appointment = factory.SubFactory(AppointmentFactory, status=Appointment.Status.COMPLETED)
    doctor = factory.SelfAttribute("appointment.doctor")
    diagnosis = factory.Faker("sentence", nb_words=8)
    notes = factory.Faker("paragraph", nb_sentences=3)
    requested_tests = factory.Faker("sentence", nb_words=5)
    summary_for_patient = factory.Faker("paragraph", nb_sentences=2)


class PrescriptionItemFactory(DjangoModelFactory):
    class Meta:
        model = PrescriptionItem

    consultation_record = factory.SubFactory(ConsultationRecordFactory)
    drug_name = factory.Faker("word")
    dose = factory.Iterator(["5mg", "10mg", "20mg", "1 tablet"])
    duration = factory.Iterator(["3 days", "5 days", "1 week", "2 weeks"])
    instructions = factory.Faker("sentence", nb_words=6)


class RequestedTestFactory(DjangoModelFactory):
    class Meta:
        model = RequestedTest

    consultation_record = factory.SubFactory(ConsultationRecordFactory)
    test_name = factory.Iterator(["CBC", "Lipid Profile", "X-Ray", "MRI", "Liver Function Test"])
    notes = factory.Faker("sentence", nb_words=5)