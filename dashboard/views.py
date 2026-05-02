import csv
import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import RedirectView, TemplateView, View

from accounts.mixins import AdminRequiredMixin, DoctorRequiredMixin, ReceptionistRequiredMixin
from accounts.models import AdminProfile, PatientProfile, ReceptionistProfile, User
from accounts.utils import ROLE_NAMES, get_user_role
from accounts.views import AdminDashboardView as AccountsAdminDashboardView
from appointments.models import Appointment

from . import services, exporters, selectors
from .forms import UserCreateForm, UserUpdateForm


class UserListView(AdminRequiredMixin, View):
	def get(self, request):
		role_filter = request.GET.get("role")
		users = User.objects.all().order_by("username")

		role_map = {user.id: get_user_role(user) or "unassigned" for user in users}

		if role_filter in ROLE_NAMES:
			users = [user for user in users if role_map.get(user.id) == role_filter]

		user_rows = [{"user": user, "role": role_map.get(user.id, "unassigned")} for user in users]

		return render(
			request,
			"dashboard/users_list.html",
			{
				"user_rows": user_rows,
				"role_filter": role_filter,
				"roles": ROLE_NAMES,
			},
		)


class UserCreateView(AdminRequiredMixin, View):
	def get(self, request):
		form = UserCreateForm()
		return render(request, "dashboard/user_form.html", {"form": form, "mode": "create"})

	def post(self, request):
		form = UserCreateForm(request.POST)
		if form.is_valid():
			user = form.save()
			return redirect("dashboard:user_detail", pk=user.id)
		return render(request, "dashboard/user_form.html", {"form": form, "mode": "create"})


class UserDetailView(AdminRequiredMixin, View):
	def get(self, request, pk):
		user = get_object_or_404(User, pk=pk)
		role = get_user_role(user)
		return render(
			request,
			"dashboard/user_detail.html",
			{"user_item": user, "role": role},
		)


class UserUpdateView(AdminRequiredMixin, View):
	def get(self, request, pk):
		user = get_object_or_404(User, pk=pk)
		role = get_user_role(user)
		
		initial_data = {"role": role}

		if role == "receptionist" and hasattr(user, "receptionist_profile"):
			initial_data["employee_code"] = user.receptionist_profile.employee_code
		elif role == "admin" and hasattr(user, "admin_profile"):
			initial_data["employee_code"] = user.admin_profile.employee_code
		elif role == "doctor" and hasattr(user, "doctor_profile"):
			initial_data["specialization"] = user.doctor_profile.specialization
			initial_data["license_number"] = user.doctor_profile.license_number
			initial_data["consultation_fee"] = user.doctor_profile.consultation_fee
		elif role == "patient" and hasattr(user, "patient_profile"):
			initial_data["date_of_birth"] = user.patient_profile.date_of_birth
			initial_data["gender"] = user.patient_profile.gender

		form = UserUpdateForm(
			instance=user,
			initial=initial_data,
			original_role=role,
		)
		return render(request, "dashboard/user_form.html", {"form": form, "mode": "edit", "user_item": user})

	def post(self, request, pk):
		user = get_object_or_404(User, pk=pk)
		role = get_user_role(user)
		form = UserUpdateForm(request.POST, instance=user, original_role=role)
		if form.is_valid():
			form.save()
			return redirect("dashboard:user_detail", pk=user.id)
		return render(request, "dashboard/user_form.html", {"form": form, "mode": "edit", "user_item": user})


def export_users_csv_view(request):
	if not request.user.is_authenticated:
		return redirect("accounts:staff_login")
	if get_user_role(request.user) != "admin" and not request.user.is_superuser:
		return redirect("dashboard:index")

	return exporters.export_users_csv()



class UserManagementRedirectView(UserPassesTestMixin, RedirectView):
    pattern_name = "admin:accounts_user_changelist"
    permanent = False

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.is_superuser or hasattr(user, "admin_profile")
        )



class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name       = 'dashboard/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(services.get_admin_dashboard_data())

        ctx['appointments_last_30_json'] = json.dumps(
            list(selectors.get_appointments_last_n_days(30)), cls=DjangoJSONEncoder)
        ctx['peak_hours_json'] = json.dumps(
            list(selectors.get_peak_hours()), cls=DjangoJSONEncoder)
        ctx['revenue_last_6_json'] = json.dumps(
            list(selectors.get_revenue_last_n_months(6)), cls=DjangoJSONEncoder)
        ctx['noshow_per_doctor_json'] = json.dumps(
            selectors.get_noshow_rate_per_doctor(), cls=DjangoJSONEncoder)

        ctx['vol_7d_json']  = json.dumps(list(selectors.get_appointments_last_n_days(7)),  cls=DjangoJSONEncoder)
        ctx['vol_90d_json'] = json.dumps(list(selectors.get_appointments_last_n_days(90)), cls=DjangoJSONEncoder)
        ctx['rev_3m_json']  = json.dumps(list(selectors.get_revenue_last_n_months(3)),     cls=DjangoJSONEncoder)
        ctx['rev_12m_json'] = json.dumps(list(selectors.get_revenue_last_n_months(12)),    cls=DjangoJSONEncoder)
        
        ctx['rev_7d_json']  = json.dumps(list(selectors.get_revenue_last_n_days(7)), cls=DjangoJSONEncoder)
        ctx['rev_30d_json'] = json.dumps(list(selectors.get_revenue_last_n_days(30)), cls=DjangoJSONEncoder)
        ctx['rev_90d_json'] = json.dumps(list(selectors.get_revenue_last_n_days(90)), cls=DjangoJSONEncoder)


        all_dates = list(selectors.get_appointments_all_dates(years_back=3))
        ctx['all_dates_json']   = json.dumps(all_dates, cls=DjangoJSONEncoder)
        all_revenue = list(selectors.get_revenue_all_months(years_back=3))
        ctx['all_revenue_json'] = json.dumps(all_revenue, cls=DjangoJSONEncoder)
        
        all_revenue_dates = list(selectors.get_revenue_all_dates(years_back=3))
        ctx['all_revenue_dates_json'] = json.dumps(all_revenue_dates, cls=DjangoJSONEncoder)
        
        ctx['available_years']  = sorted(set(d['date'].year for d in all_dates), reverse=True)

        appts_30 = ctx['appointments_last_30']
        total_30d = sum(d['count'] for d in appts_30)
        ctx['analytics_total_30d'] = total_30d
        ctx['analytics_avg_daily']  = round(total_30d / 30, 1)
        peak_hrs = ctx['peak_hours']
        if peak_hrs:
            h = peak_hrs[0]['hour']
            ctx['analytics_peak_hour'] = ('12 AM' if h == 0 else f'{h} AM' if h < 12 else '12 PM' if h == 12 else f'{h - 12} PM')
        else:
            ctx['analytics_peak_hour'] = '—'
        noshow = ctx['noshow_summary']
        completed = noshow['total'] - noshow['noshows']
        ctx['analytics_completed_30d'] = completed
        

        revenue_30d = completed * 150.00

        if revenue_30d >= 1000000:
            ctx['analytics_revenue_30d'] = f"${revenue_30d / 1000000:.2f}m"
        elif revenue_30d >= 1000:
            ctx['analytics_revenue_30d'] = f"${revenue_30d / 1000:.1f}k"
        else:
            ctx['analytics_revenue_30d'] = f"${revenue_30d:.2f}"
            
        ctx['active_tab'] = self.request.GET.get('tab', 'overview')
        return ctx


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    template_name       = 'dashboard/doctor_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(services.get_doctor_dashboard_data(self.request.user))
        return ctx


class ReceptionistDashboardView(ReceptionistRequiredMixin, TemplateView):
    template_name       = 'dashboard/receptionist_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(services.get_receptionist_dashboard_data())
        return ctx


class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        role = get_user_role(user)

        if role == 'admin':
            return redirect('dashboard:admin')

        if role == 'doctor':
            return redirect('dashboard:doctor')

        if role == 'receptionist':
            return redirect('dashboard:receptionist')

        return redirect('accounts:patient_dashboard')




class ReportsView(AdminRequiredMixin, View):

    def get(self, request):
        appt_filters = {
            'status':    request.GET.get('status', ''),
            'date_from': request.GET.get('date_from', ''),
            'date_to':   request.GET.get('date_to', ''),
            'doctor_id': request.GET.get('doctor_id', ''),
            'search':    request.GET.get('search', ''),
        }
        appointments = selectors.get_filtered_appointments(
            status=appt_filters['status'] or None,
            date_from=appt_filters['date_from'] or None,
            date_to=appt_filters['date_to'] or None,
            doctor_id=int(appt_filters['doctor_id']) if appt_filters['doctor_id'] else None,
            search=appt_filters['search'] or None,
        )
        appt_paginator = Paginator(appointments, 20)
        appt_page      = appt_paginator.get_page(request.GET.get('page', 1))

        return render(request, 'dashboard/reports.html', {
            'appt_page':     appt_page,
            'doctors':       selectors.get_all_doctors(),
            'status_list':   ['REQUESTED', 'CONFIRMED', 'CHECKED_IN', 'COMPLETED', 'CANCELLED', 'NO_SHOW'],
            'appt_filters':  appt_filters,
        })



class ExportAppointmentsView(AdminRequiredMixin, View):

    def get(self, request):
        qs = selectors.get_filtered_appointments(
            status=request.GET.get('status') or None,
            date_from=request.GET.get('date_from') or None,
            date_to=request.GET.get('date_to') or None,
            doctor_id=int(request.GET.get('doctor_id')) if request.GET.get('doctor_id') else None,
            search=request.GET.get('search') or None,
        )
        return exporters.export_appointments_csv(qs=qs)


class ExportNoshowReportView(AdminRequiredMixin, View):

    def get(self, request):
        try:
            days = int(request.GET.get('days', 30))
        except (ValueError, TypeError):
            days = 30
        return exporters.export_noshow_report_csv(days_back=days)


class ExportRevenueReportView(AdminRequiredMixin, View):

    def get(self, request):
        try:
            months = int(request.GET.get('months', 6))
        except (ValueError, TypeError):
            months = 6
        return exporters.export_revenue_report_csv(months=months)
