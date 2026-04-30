from django import forms
from django.forms import inlineformset_factory
from .models import ConsultationRecord, PrescriptionItem, RequestedTest
from django.core.validators import MinLengthValidator


class ConsultationRecordForm(forms.ModelForm):

    class Meta:
        model = ConsultationRecord
        fields = ['diagnosis', 'notes', 'requested_tests', 'summary_for_patient']
        widgets = {
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter patient diagnosis...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Clinical examination notes...'
            }),
            'requested_tests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Requested tests...',
                'form': 'consultationForm'
            }),
            'summary_for_patient': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Summary to be given to patient...'
            }),
        }

    def clean_diagnosis(self):
        diagnosis = self.cleaned_data.get('diagnosis')
        if diagnosis and len(diagnosis.strip()) < 10:
            raise forms.ValidationError("Diagnosis must be at least 10 characters.")
        return diagnosis


class PrescriptionItemForm(forms.ModelForm):

    FREQUENCY_CHOICES = [
        ('OD', 'Once Daily'),
        ('BD', 'Twice Daily'),
        ('TDS', 'Three Times Daily'),
        ('QDS', 'Four Times Daily'),
        ('PRN', 'As Needed'),
    ]

    frequency = forms.ChoiceField(
        choices=FREQUENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Frequency'
    )

    class Meta:
        model = PrescriptionItem
        fields = ['drug_name', 'dose', 'duration', 'frequency', 'instructions']
        widgets = {
            'drug_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Drug name...'
            }),
            'dose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500mg'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 7 days'
            }),
            'instructions': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Special instructions (optional)'
            }),
        }

    def clean_drug_name(self):
        drug_name = self.cleaned_data.get('drug_name')
        if drug_name and len(drug_name.strip()) < 3:
            raise forms.ValidationError("Drug name must be at least 3 characters.")
        return drug_name


class RequestedTestForm(forms.ModelForm):

    URGENCY_CHOICES = [
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    ]

    urgency = forms.ChoiceField(
        choices=URGENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Urgency'
    )

    class Meta:
        model = RequestedTest
        fields = ['test_name', 'urgency', 'notes']
        widgets = {
            'test_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Test name (e.g., CBC, Blood Sugar)...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Instructions for lab (optional)...'
            }),
        }

    def clean_test_name(self):
        test_name = self.cleaned_data.get('test_name')
        if test_name and len(test_name.strip()) < 3:
            raise forms.ValidationError("Test name must be at least 3 characters.")
        return test_name

PrescriptionItemFormSet = inlineformset_factory(
    ConsultationRecord, PrescriptionItem,
    form=PrescriptionItemForm,
    extra=0,
    can_delete=True
)

RequestedTestFormSet = inlineformset_factory(
    ConsultationRecord, RequestedTest,
    form=RequestedTestForm,
    extra=0,
    can_delete=True
)
