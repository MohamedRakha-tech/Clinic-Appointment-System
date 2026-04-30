from django.db import models
from django.conf import settings


class AuditLog(models.Model):


    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN',  'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=50)   
    target_id   = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)        
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    extra_data  = models.JSONField(default=dict, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dashboard_audit_log'
        ordering = ['-timestamp']   
        indexes  = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['target_model', 'target_id']),
            models.Index(fields=['action', 'timestamp']),
        ]
        permissions = [
        ('view_analytics',            'Can view analytics dashboard'),
        ('view_doctor_dashboard',     'Can view doctor dashboard'),
        ('view_receptionist_dashboard','Can view receptionist dashboard'),
        ('export_data',               'Can export CSV reports'),
    ]

    def __str__(self):
        return f"{self.user} | {self.action} | {self.target_model}:{self.target_id}"

    @classmethod
    def log(cls, user, action, target_model, target_id=None,
            description='', ip_address=None, extra_data=None):

        
        return cls.objects.create(
            user=user,
            action=action,
            target_model=target_model,
            target_id=target_id,
            description=description,
            ip_address=ip_address,
            extra_data=extra_data or {},
        )