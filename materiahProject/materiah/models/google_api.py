from django.db import models
from django_cryptography.fields import encrypt
from django.contrib.auth.models import User


class GoogleCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='google_credentials')
    refresh_token = encrypt(models.CharField(max_length=255, null=True))
    access_token = encrypt(models.CharField(max_length=255, null=True))
    token_expiry = models.DateTimeField(null=True)
