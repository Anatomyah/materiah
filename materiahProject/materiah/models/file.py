from django.db import models


class FileUploadStatus(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    quote = models.OneToOneField('Quote', on_delete=models.CASCADE, null=True, blank=True)
    product_image = models.OneToOneField('ProductImage', on_delete=models.CASCADE, null=True, blank=True)
    order_receipt = models.OneToOneField('OrderImage', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.status} - Created at: {self.created_at}"
