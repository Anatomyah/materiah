from django.contrib.auth.models import User
from django.db import models

from ..config import PHONE_PREFIX_CHOICES
from .custom_validators import validate_phone_suffix
from .supplier import Supplier


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_prefix = models.CharField(max_length=3, choices=PHONE_PREFIX_CHOICES, default='050')
    phone_suffix = models.CharField(max_length=7, validators=[validate_phone_suffix])

    def __str__(self):
        return f"{self.user}"


class SupplierUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE)
    contact_phone_prefix = models.CharField(max_length=3, choices=PHONE_PREFIX_CHOICES, default='050', blank=True,
                                            null=True)
    contact_phone_suffix = models.CharField(max_length=7, validators=[validate_phone_suffix], blank=True, null=True)

    def __str__(self):
        return f"{self.user}"
