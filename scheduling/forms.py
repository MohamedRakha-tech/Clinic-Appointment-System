from django import forms

from scheduling.models import DoctorScheduleException, DoctorWeeklySchedule


class DoctorWeeklyScheduleForm(forms.ModelForm):
    class Meta:
        model = DoctorWeeklySchedule
        fields = [
            "doctor",
            "day_of_week",
            "start_time",
            "end_time",
            "is_active",
        ]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        day_of_week = cleaned_data.get("day_of_week")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if day_of_week is not None and not 0 <= day_of_week <= 6:
            self.add_error("day_of_week", "Day of week must be between 0 and 6.")

        if start_time and end_time and start_time >= end_time:
            self.add_error("start_time", "Start time must be before end time.")

        return cleaned_data


class DoctorScheduleExceptionForm(forms.ModelForm):
    class Meta:
        model = DoctorScheduleException
        fields = [
            "doctor",
            "exception_date",
            "type",
            "start_time",
            "end_time",
            "reason",
        ]
        widgets = {
            "exception_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        exception_type = cleaned_data.get("type")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if exception_type == DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY:
            if not start_time:
                self.add_error("start_time", "Start time is required for a special working day.")
            if not end_time:
                self.add_error("end_time", "End time is required for a special working day.")

        if start_time and end_time and start_time >= end_time:
            self.add_error("start_time", "Start time must be before end time.")

        return cleaned_data
