from random import choice

from accounts.factories import UserFactory
from notifications.models import Notification


def NotificationFactory(**kwargs):
    recipient = kwargs.pop("recipient", None) or UserFactory()
    target = kwargs.pop("target", None)

    if target is not None:
        from django.contrib.contenttypes.models import ContentType

        kwargs.setdefault("target_content_type", ContentType.objects.get_for_model(target))
        kwargs.setdefault("target_object_id", str(target.pk))

    kwargs.setdefault(
        "verb",
        choice(
            [
                "appointment_confirmed",
                "appointment_checked_in",
                "appointment_completed",
                "new_message",
            ]
        ),
    )
    kwargs.setdefault(
        "description",
        choice(
            [
                "A new event is available for review.",
                "The appointment status has been updated.",
                "You have an unread update in the system.",
                "A related record was just created.",
            ]
        ),
    )
    kwargs.setdefault("is_read", False)

    return Notification.objects.create(recipient=recipient, **kwargs)