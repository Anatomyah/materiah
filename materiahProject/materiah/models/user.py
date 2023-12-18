from django.contrib.auth.models import User
from django.db import models

from .config import PHONE_PREFIX_CHOICES
from .custom_validators import validate_phone_suffix
from .supplier import Supplier


class UserProfile(models.Model):
    """
      Represents a user profile with additional fields linked to Django's default User model.

      Attributes:
          user (OneToOneField): A one-to-one relationship with Django's User model.
          phone_prefix (CharField): The prefix part of the user's phone number. Choices from PHONE_PREFIX_CHOICES.
          phone_suffix (CharField): The suffix or main part of the user's phone number. Validated by validate_phone_suffix.

      Meta:
          unique_together: Ensures that the combination of phone_prefix and phone_suffix is unique across all user profiles.
      """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_prefix = models.CharField(max_length=3, choices=PHONE_PREFIX_CHOICES, default='050')
    phone_suffix = models.CharField(max_length=7, validators=[validate_phone_suffix])

    def __str__(self):
        return f"{self.user}"

    class Meta:
        unique_together = ('phone_prefix', 'phone_suffix')


class SupplierUserProfile(models.Model):
    """
        Represents a supplier user profile linked to Django's default User model and the Supplier model.
        It includes contact details specific to supplier representatives.

        Attributes:
            user (OneToOneField): A one-to-one relationship with Django's User model.
            supplier (OneToOneField): A one-to-one relationship with the Supplier model.
            contact_phone_prefix (CharField): The prefix part of the contact phone number. Choices from PHONE_PREFIX_CHOICES.
                Optional.
            contact_phone_suffix (CharField): The suffix or main part of the contact phone number.
                Validated by validate_phone_suffix. Optional.

        Meta:
            unique_together: Ensures that the combination of contact_phone_prefix and contact_phone_suffix
            is unique across all supplier user profiles.
        """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE)
    contact_phone_prefix = models.CharField(max_length=3, choices=PHONE_PREFIX_CHOICES, default='050', blank=True,
                                            null=True)
    contact_phone_suffix = models.CharField(max_length=7, validators=[validate_phone_suffix], blank=True, null=True)

    def __str__(self):
        return f"{self.user}"

    class Meta:
        unique_together = ('contact_phone_prefix', 'contact_phone_suffix')
