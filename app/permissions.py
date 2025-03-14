from rest_framework import permissions

class IsClinicAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'

class IsSameClinicUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.clinic == request.user.clinic 