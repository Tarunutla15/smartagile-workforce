from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user (AUTH_USER_MODEL). Replaces legacy SignupData."""

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=50, default="employee")
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.email
