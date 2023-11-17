from django.db import models

"""
   Model to track the status of file uploads.

   This model is used to monitor and record the status of file uploads to AWS S3. 
   It tracks various types of files related to quotes, product images, and order receipts. 
   A background task runs every 10 minutes to clean out records that were not processed 
   normally due to errors.

   Attributes:
   - status (CharField): Indicates the current status of the file upload. 
     The possible statuses are 'pending', 'uploading', 'completed', and 'failed'.
   - created_at (DateTimeField): The date and time when the file upload record was created.
     Automatically set to the current date and time when a record is created.
   - quote (OneToOneField): A one-to-one relationship to the 'Quote' model. 
     This field can be null or blank, indicating the file upload may or may not be associated with a quote.
   - product_image (OneToOneField): A one-to-one relationship to the 'ProductImage' model. 
     This field can be null or blank, indicating the file upload may or may not be associated with a product image.
   - order_receipt (OneToOneField): A one-to-one relationship to the 'OrderImage' model. 
     This field can be null or blank, indicating the file upload may or may not be associated with an order receipt.

   Methods:
   - __str__(self): Returns a string representation of the instance, including the status 
     and the creation date and time.

   Usage:
   - Used by an automated process to manage and clean file upload records.
   - Interacts with related 'Quote', 'ProductImage', and 'OrderImage' models as needed.
   """


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
