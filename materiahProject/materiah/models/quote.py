from django.conf import settings
from django.db import models

from .file import FileUploadStatus
from .product import Product
from .supplier import Supplier


class Quote(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('RECEIVED', 'Received'),
        ('ARRIVED, UNFULFILLED', 'Arrived, unfulfilled'),
        ('FULFILLED', 'Fulfilled'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    request_date = models.DateField(auto_now_add=True, null=True)
    creation_date = models.DateField(auto_now_add=True)
    last_updated = models.DateField(auto_now=True, null=True)
    quote_url = models.URLField(max_length=1024, editable=False, blank=True)
    s3_quote_key = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')

    def __str__(self):
        return f"{self.id}"

    def save(self, *args, **kwargs):
        if not self.quote_url and self.s3_quote_key:
            self.quote_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.s3_quote_key}'
        super(Quote, self).save(*args, **kwargs)


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
