"""
Central registry of custom business-logic permissions for the clinic app.

Each permission is stored on the User model's Meta.permissions so Django
creates the corresponding Permission rows during migrate.

Format: {codename: verbose_name}
"""


class BusinessPermissions:
    # ── Patient / EMR ──────────────────────────────────────────────────────
    VIEW_PATIENT_PROFILE   = ("view_patientprofile",   "Can view patient profile")
    CHANGE_PATIENT_PROFILE = ("change_patientprofile", "Can change patient profile")

    # ── Doctor ─────────────────────────────────────────────────────────────
    VIEW_DOCTOR_PROFILE   = ("view_doctorprofile",   "Can view doctor profile")
    CHANGE_DOCTOR_PROFILE = ("change_doctorprofile", "Can change doctor profile")

    # ── Appointments ───────────────────────────────────────────────────────
    VIEW_APPOINTMENT   = ("view_appointment",   "Can view appointment")
    ADD_APPOINTMENT    = ("add_appointment",    "Can add appointment")
    CHANGE_APPOINTMENT = ("change_appointment", "Can change appointment")
    DELETE_APPOINTMENT = ("delete_appointment", "Can delete appointment")

    # ── Receptionist ───────────────────────────────────────────────────────
    VIEW_RECEPTIONIST_PROFILE = ("view_receptionistprofile", "Can view receptionist profile")

    # ── Admin ──────────────────────────────────────────────────────────────
    VIEW_ADMIN_PROFILE = ("view_adminprofile", "Can view admin profile")

    @classmethod
    def all_permissions(cls) -> dict:
        """
        Return {codename: verbose_name} for every permission defined on this
        class (all class-level tuples).
        """
        result = {}
        for attr_name in dir(cls):
            if attr_name.startswith("_"):
                continue
            value = getattr(cls, attr_name)
            if isinstance(value, tuple) and len(value) == 2:
                codename, verbose_name = value
                result[codename] = verbose_name
        return result
