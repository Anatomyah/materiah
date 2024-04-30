from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import product_views, manufacturer_views, supplier_views, user_views, order_views, quote_views, \
    notification_views, email_template_views, messages_views
from .views.user_views import CustomObtainAuthToken

# Viewsets registration
router = DefaultRouter()
router.register(r'products', product_views.ProductViewSet, basename='product')
router.register(r'manufacturers', manufacturer_views.ManufacturerViewSet, basename='manufacturer')
router.register(r'suppliers', supplier_views.SupplierViewSet, basename='supplier')
router.register(r'users', user_views.UserViewSet, basename='user')
router.register(r'orders', order_views.OrderViewSet, basename='order')
router.register(r'quotes', quote_views.QuoteViewSet, basename='quotes')
router.register(r'order_notifications', notification_views.OrderNotificationViewSet, basename='order_notifications')
router.register(r'expiry_notifications', notification_views.ExpiryNotificationViewSet, basename='expiry_notifications')

# Custom Views registrations
urlpatterns = [
    path('', include(router.urls)),
    path('api-token-auth/', CustomObtainAuthToken.as_view(), name='api_token_auth'),
    path('logout/', user_views.LogoutAPIView.as_view(), name='logout'),
    path('api/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('update_email_signature/', email_template_views.update_email_signature, name='update_email_template'),
    path('fetch_email_signature/', email_template_views.fetch_email_signature, name='fetch_email_template'),
    path('get_messages/', messages_views.get_messages, name='get_messages'),
    path('download_attachment/', messages_views.get_attachment, name='get_attachment'),
    path('send_message/', messages_views.send_message, name='send_message'),
    path('pubsub_push/', messages_views.pubsub_push, name='pubsub_push'),
    path('mark_email_as_read/', messages_views.mark_email_as_read, name='mark_email_as_read'),
    path('mark_email_as_unread/', messages_views.mark_email_as_unread, name='mark_email_as_unread'),
    path('bulk_mark_email_as_read/', messages_views.bulk_mark_email_as_read, name='bulk_mark_email_as_read'),
    path('bulk_mark_email_as_unread/', messages_views.bulk_mark_email_as_unread, name='bulk_mark_email_as_unread'),
    path('bulk_delete_email/', messages_views.bulk_delete_email, name='bulk_delete_email'),
]
