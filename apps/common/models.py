from django.db import models

from apps.accounts.models import User

# ─────────────────────────────────────────────
# SYSTEM TABLES
# ─────────────────────────────────────────────

class AuditLog(models.Model):
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action      = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id   = models.CharField(max_length=50)
    description = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        indexes  = [
            models.Index(fields=["action", "created_at"], name="idx_audit_action_created"),
        ]

    def __str__(self):
        return f"{self.action} on {self.target_type} #{self.target_id}"


class SystemSetting(models.Model):
    key         = models.CharField(max_length=100, unique=True)
    value       = models.TextField()
    description = models.CharField(max_length=255, blank=True, null=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"