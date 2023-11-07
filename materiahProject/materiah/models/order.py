from django.conf import settings
from django.db import models

from .file import FileUploadStatus
from .quote import Quote, QuoteItem


class Order(models.Model):
    quote = models.OneToOneField(to=Quote, on_delete=models.SET_NULL, null=True)
    arrival_date = models.DateField()
    received_by = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f"{self.id}"


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('OK', 'OK'),
        ('Did not arrive', 'Did not arrive'),
        ('Different amount', 'Different amount'),
        ('Wrong Item', 'Wrong Item'),
        ('Expired or near expiry', 'Expired or near expiry'),
        ('Bad condition', 'Bad condition'),
        ('Other', 'Other'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    quote_item = models.OneToOneField(QuoteItem, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    batch = models.CharField(max_length=50, blank=True, null=True)
    expiry = models.DateField(blank=True, null=True)
    status = models.CharField('status', max_length=22,
                              choices=STATUS_CHOICES, default='OK')
    issue_detail = models.CharField(max_length=250, null=True)


class OrderImage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    image_url = models.URLField(max_length=1024, editable=False, blank=True)
    s3_image_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if not self.image_url:
            self.image_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.s3_image_key}'
        super(OrderImage, self).save(*args, **kwargs)
