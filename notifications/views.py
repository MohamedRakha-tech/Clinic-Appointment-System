from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import Notification


class NotificationListView(LoginRequiredMixin, View):
	login_url = "/accounts/patient/login/"

	def get(self, request):
		status_filter = request.GET.get("status", "all")
		notifications = Notification.objects.filter(recipient=request.user)

		if status_filter == "unread":
			notifications = notifications.filter(is_read=False)
		elif status_filter == "read":
			notifications = notifications.filter(is_read=True)

		unread_count = Notification.objects.filter(
			recipient=request.user,
			is_read=False,
		).count()

		return render(
			request,
			"notifications/list.html",
			{
				"notifications": notifications,
				"status_filter": status_filter,
				"unread_count": unread_count,
			},
		)


class NotificationMarkReadView(LoginRequiredMixin, View):
	login_url = "/accounts/patient/login/"

	def post(self, request, notification_id):
		notification = get_object_or_404(
			Notification,
			pk=notification_id,
			recipient=request.user,
		)

		if not notification.is_read:
			notification.is_read = True
			notification.save(update_fields=["is_read"])
			messages.success(request, "Notification marked as read.")

		return redirect("notifications:list")


class NotificationMarkAllReadView(LoginRequiredMixin, View):
	login_url = "/accounts/patient/login/"

	def post(self, request):
		updated = Notification.objects.filter(
			recipient=request.user,
			is_read=False,
		).update(is_read=True)

		if updated:
			messages.success(request, "All notifications marked as read.")

		return redirect("notifications:list")
