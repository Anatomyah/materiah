from django.db import models

from .config import PHONE_PREFIX_CHOICES
from .custom_validators import validate_phone_suffix


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    website = models.URLField()
    email = models.EmailField()
    phone_prefix = models.CharField(max_length=3, choices=PHONE_PREFIX_CHOICES, default='02')
    phone_suffix = models.CharField(max_length=7, validators=[validate_phone_suffix])

    def __str__(self):
        return f"{self.name}"
