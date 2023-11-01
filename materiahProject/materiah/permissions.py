from rest_framework.permissions import BasePermission


class ProfileTypePermission(BasePermission):
    def has_permission(self, request, view):
        request.is_supplier = hasattr(request.user, 'supplieruserprofile')

        return True


class DenySupplierProfile(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'userprofile')
