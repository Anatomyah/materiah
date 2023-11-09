from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

from .models import Manufacturer, Supplier, Product, Order, Quote


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    user_email = reset_password_token.user.email
    token = reset_password_token.key

    html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Password Reset</title>
        </head>
        <body>
            <h1>Password Reset</h1>
            <p>Hello,</p>
            <p>You are receiving this email because we received a password reset request for your account.</p>
            <p>Below is the token in order to reset your password:</p>
            <h1>{token}</h1>
            <p>If you did not request a password reset, please ignore this email.</p>
            <p>Thank you,</p>
            <p>The Materiah Team</p>
        </body>
        </html>
        """

    send_mail(
        'Password Reset',
        'Please follow the instructions in the HTML content to reset your password.',
        'motdekar@gmail.com',
        [user_email],
        fail_silently=False,
        html_message=html_content
    )


@receiver(post_save, sender=User)
@receiver(post_delete, sender=User)
def invalidate_user_list_cache(sender, **kwargs):
    keys = cache.get('user_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('user_list_keys', [])


@receiver(post_save, sender=Manufacturer)
@receiver(post_delete, sender=Manufacturer)
def invalidate_manufacturer_list_cache(sender, **kwargs):
    keys = cache.get('manufacturers_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('manufacturers_list_keys', [])


@receiver(post_save, sender=Supplier)
@receiver(post_delete, sender=Supplier)
def invalidate_supplier_list_cache(sender, **kwargs):
    keys = cache.get('suppliers_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('suppliers_list_keys', [])


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_product_list_cache(sender, **kwargs):
    keys = cache.get('products_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('products_list_keys', [])


@receiver(post_save, sender=Order)
@receiver(post_delete, sender=Order)
def invalidate_order_list_cache(sender, **kwargs):
    keys = cache.get('orders_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('orders_list_keys', [])


@receiver(post_save, sender=Quote)
@receiver(post_delete, sender=Quote)
def invalidate_quote_list_cache(sender, **kwargs):
    keys = cache.get('quotes_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('quotes_list_keys', [])


@receiver(pre_save, sender=User)
def ensure_unique_email_and_username(sender, instance, **kwargs):
    if User.objects.filter(email=instance.email).exclude(id=instance.id).exists():
        raise ValidationError("A user with that email already exists.")

    if User.objects.filter(username=instance.username).exclude(id=instance.id).exists():
        raise ValidationError("A user with that username already exists.")
