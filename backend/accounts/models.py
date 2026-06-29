from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user (AUTH_USER_MODEL). Replaces legacy SignupData."""

    DIGEST_OFF = "off"
    DIGEST_DAILY = "daily"
    DIGEST_WEEKLY = "weekly"
    DIGEST_CHOICES = [
        (DIGEST_OFF, "Off"),
        (DIGEST_DAILY, "Daily"),
        (DIGEST_WEEKLY, "Weekly"),
    ]

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=50, default="employee")
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    # Recurring usage-report digest cadence emailed by the scheduling agent (Celery beat).
    digest_frequency = models.CharField(
        max_length=10, choices=DIGEST_CHOICES, default=DIGEST_OFF
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.email
