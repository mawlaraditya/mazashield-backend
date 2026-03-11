from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'SuperAdmin' and 
            request.user.deleted_at is None
        )

class IsMarketingOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['Marketing', 'SuperAdmin', 'CEO', 'Komisaris'] and 
            request.user.deleted_at is None
        )

class IsActiveUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active and 
            request.user.deleted_at is None
        )

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'Customer' and 
            request.user.deleted_at is None
        )
