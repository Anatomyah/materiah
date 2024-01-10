from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

from .models import Manufacturer, Supplier, Product, Order, Quote, ProductItem


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    :param sender: the sender of the signal
    :param instance: the instance triggering the signal
    :param reset_password_token: the password reset token
    :param args: additional positional arguments
    :param kwargs: additional keyword arguments
    :return: None

    This method is a receiver for the `reset_password_token_created` signal. It sends an email to the user with the password reset token.

    The email contains an HTML message that includes the token and instructions for resetting the password. The email is sent to the email address associated with the user's account.
    """
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


@receiver(post_save, sender=Manufacturer)
@receiver(post_delete, sender=Manufacturer)
def invalidate_manufacturer_list_cache(sender, **kwargs):
    """
    Invalidates the cache for the manufacturer list.

    :param sender: The sender of the signal.
    :param kwargs: Additional keyword arguments.
    :return: None
    """
    keys = cache.get('manufacturer_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('manufacturer_list_keys', [])


@receiver(post_save, sender=Supplier)
@receiver(post_delete, sender=Supplier)
def invalidate_supplier_list_cache(sender, **kwargs):
    """
    Invalidates the cache for the supplier list.

    :param sender: The sender of the signal.
    :param kwargs: Additional keyword arguments passed to the method.
    :return: None

    """
    keys = cache.get('supplier_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('supplier_list_keys', [])


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
@receiver(post_save, sender=ProductItem)
@receiver(post_delete, sender=ProductItem)
def invalidate_product_list_cache(sender, **kwargs):
    """
    Invalidates the product list cache when a product is saved or deleted or when a stock item related to a product is
    saved or deleted.

    :param sender: The sender model instance.
    :param kwargs: The keyword arguments passed to the signal handler.
    :return: None
    """
    keys = cache.get('product_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('product_list_keys', [])


@receiver(post_save, sender=Order)
@receiver(post_delete, sender=Order)
def invalidate_order_list_cache(sender, **kwargs):
    """
    Invalidates the cache for the order list.

    .. note::
        This method is a signal receiver that should be connected to the ``post_save`` and ``post_delete`` signals of the ``Order`` model.

    :param sender: The sender of the signal.
    :param kwargs: Any additional keyword arguments.
    :return: None
    """
    keys = cache.get('order_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('order_list_keys', [])


@receiver(post_save, sender=Quote)
@receiver(post_delete, sender=Quote)
def invalidate_quote_list_cache(sender, **kwargs):
    """
    Invalidate the quote_list cache based on the specified sender and kwargs.

    :param sender: The sender of the signal.
    :param kwargs: Keyword arguments for the signal.
    :return: None
    """
    keys = cache.get('quote_list_keys', [])
    for key in keys:
        cache.delete(key)
    cache.set('quote_list_keys', [])


@receiver(pre_save, sender=User)
def ensure_unique_email_and_username(sender, instance, **kwargs):
    """
    Ensure that the email and username of a user are unique.

    :param sender: The sender of the signal.
    :type sender: Any
    :param instance: The instance of the user being saved.
    :type instance: User
    :param kwargs: Additional keyword arguments.
    :type kwargs: Dict[str, Any]
    :raises ValidationError: If a user with the same email or username already exists.
    """
    if User.objects.filter(email=instance.email).exclude(id=instance.id).exists():
        raise ValidationError("A user with that email already exists.")

    if User.objects.filter(username=instance.username).exclude(id=instance.id).exists():
        raise ValidationError("A user with that username already exists.")
