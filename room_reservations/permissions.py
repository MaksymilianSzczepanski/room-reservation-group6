from rest_framework import permissions


STUDENT_GROUP_NAME = "Students"


def can_create_reservations(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return not user.groups.filter(name=STUDENT_GROUP_NAME).exists()


class StudentsReadOnlyReservationPermission(permissions.BasePermission):
    message = "Studenci moga tylko przegladac rezerwacje sal."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return can_create_reservations(request.user)
