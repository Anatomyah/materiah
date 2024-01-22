from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny

from .paginator import MateriahPagination
from .permissions import DenySupplierProfile
from ..models import OrderNotifications, ExpiryNotifications
from ..serializers.notifications_serializer import OrderNotificationSerializer, ExpiryNotificationSerializer


class OrderNotificationViewSet(viewsets.ModelViewSet):
    queryset = OrderNotifications.objects.all()
    serializer_class = OrderNotificationSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'suppliers__name', 'product__name', 'product__cat_num']

    def get_permissions(self):
        """
           Overrides the method from the base class (viewsets.ModelViewSet) to implement custom permissions logic.
           This is invoked every time a request is made to the API.
           It returns a list of permission classes that should be applied to the action handler.
           This method distinguishes between an action handler that retrieves names ('names') and other authenticated actions.
           It assumes that non-authenticated actions supply an empty list of permissions.
           """
        if self.action == 'names':
            # Allow any authenticated user
            return [AllowAny()]

        elif self.request.user.is_authenticated:
            # Apply DenySupplierProfile for other actions where the user is authenticated.
            # This could be extending the logic to any action that needs specific user authorization.
            return [DenySupplierProfile()]

            # For unauthenticated requests or those not falling into the above categories, no permissions are applied.
        return []


class ExpiryNotificationViewSet(viewsets.ModelViewSet):
    queryset = ExpiryNotifications.objects.all()
    serializer_class = ExpiryNotificationSerializer
    pagination_class = MateriahPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'suppliers__name', 'product__name', 'product__cat_num']

    def get_permissions(self):
        """
           Overrides the method from the base class (viewsets.ModelViewSet) to implement custom permissions logic.
           This is invoked every time a request is made to the API.
           It returns a list of permission classes that should be applied to the action handler.
           This method distinguishes between an action handler that retrieves names ('names') and other authenticated actions.
           It assumes that non-authenticated actions supply an empty list of permissions.
           """
        if self.action == 'names':
            # Allow any authenticated user
            return [AllowAny()]

        elif self.request.user.is_authenticated:
            # Apply DenySupplierProfile for other actions where the user is authenticated.
            # This could be extending the logic to any action that needs specific user authorization.
            return [DenySupplierProfile()]

            # For unauthenticated requests or those not falling into the above categories, no permissions are applied.
        return []
