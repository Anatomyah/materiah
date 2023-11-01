from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import product_views, manufacturer_views, supplier_views, user_views, order_views, quote_views
from .views.user_views import CustomObtainAuthToken

router = DefaultRouter()
router.register(r'products', product_views.ProductViewSet, basename='product')
router.register(r'manufacturers', manufacturer_views.ManufacturerViewSet, basename='manufacturer')
router.register(r'suppliers', supplier_views.SupplierViewSet, basename='supplier')
router.register(r'users', user_views.UserViewSet, basename='user')
router.register(r'orders', order_views.OrderViewSet, basename='order')
router.register(r'quotes', quote_views.QuoteViewSet, basename='quotes')

urlpatterns = [
    path('', include(router.urls)),
    path('api-token-auth/', CustomObtainAuthToken.as_view(), name='api_token_auth'),
    path('logout', user_views.LogoutAPIView.as_view(), name='logout'),
    path('api/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
]
