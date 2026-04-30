from accounts.utils import get_user_role


def user_role_context(request):
    role = get_user_role(getattr(request, "user", None))
    return {
        "current_user_role": role,
        "can_book_appointments": role == "patient",
    }
