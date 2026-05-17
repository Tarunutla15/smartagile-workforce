from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """App-level admin (User.role == 'admin')."""

    message = "Admin role required."

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and u.is_authenticated
            and getattr(u, "role", None) == "admin"
        )
