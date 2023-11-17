from django.db import models

from .config import PHONE_PREFIX_CHOICES
from .custom_validators import validate_phone_suffix

"""
   Represents a supplier with details like name, website, email, and phone number. 
   Ensures unique identification through name, email, and a combination of phone prefix and suffix.

   Attributes:
       name (CharField): The name of the supplier. Unique.
       website (URLField): The website URL of the supplier.
       email (EmailField): The email address of the supplier. Unique.
       phone_prefix (CharField): The prefix part of the phone number. Choices from PHONE_PREFIX_CHOICES.
       phone_suffix (CharField): The suffix or main part of the phone number. Validated by validate_phone_suffix.

   Meta:
       unique_together: Ensures that the combination of phone_prefix and phone_suffix is unique across all suppliers.
   """


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    website = models.URLField()
    email = models.EmailField(unique=True)
    phone_prefix = models.CharField(max_length=3, choices=PHONE_PREFIX_CHOICES, default='02')
    phone_suffix = models.CharField(max_length=7, validators=[validate_phone_suffix])

    def __str__(self):
        return f"{self.name}"

    class Meta:
        unique_together = ('phone_prefix', 'phone_suffix')
