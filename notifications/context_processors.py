from .models import Notification


def notification_panel(request):
    if not request.user.is_authenticated:
        return {
            "notification_preview": [],
            "notification_unread_count": 0,
        }

    preview = list(
        Notification.objects.filter(recipient=request.user)
        .only("id", "verb", "description", "is_read", "created_at")
        .order_by("-created_at")[:4]
    )

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()

    return {
        "notification_preview": preview,
        "notification_unread_count": unread_count,
    }
