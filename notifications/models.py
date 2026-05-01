from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="notifications",
	)
	verb = models.CharField(max_length=120)
	description = models.TextField(blank=True)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	target_content_type = models.ForeignKey(
		ContentType,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	target_object_id = models.CharField(max_length=64, blank=True)
	target = GenericForeignKey("target_content_type", "target_object_id")

	class Meta:
		db_table = "notifications"
		indexes = [
			models.Index(fields=["recipient", "is_read", "created_at"]),
		]
		ordering = ["-created_at"]

	def __str__(self):
		return f"Notification({self.recipient_id}): {self.verb}"

	@staticmethod
	def create_for(recipient, verb, description="", target=None):
		if recipient is None:
			return None

		content_type = None
		object_id = ""

		if target is not None:
			content_type = ContentType.objects.get_for_model(target)
			object_id = str(target.pk)

		return Notification.objects.create(
			recipient=recipient,
			verb=verb,
			description=description,
			target_content_type=content_type,
			target_object_id=object_id,
		)
