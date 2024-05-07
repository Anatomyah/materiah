from django.conf import settings
from django.db import models

from .product import Product
from .supplier import Supplier


class Quote(models.Model):
    """
       Represents a quote for products from a supplier. It includes details such as the supplier,
       dates related to the quote request and update, and the status of the quote.

       Attributes:
           STATUS_CHOICES (list of tuple): Defines possible statuses for a quote.
           supplier (ForeignKey): Link to the Supplier model. Cascade deletes.
           request_date (DateField): Date when the quote was requested. Auto-set on creation.
           creation_date (DateField): Creation date of the quote record. Auto-set on creation.
           last_updated (DateField): Last date when the quote was updated. Auto-updated on save.
           quote_url (URLField): URL of the quote, auto-generated from S3 key if not provided.
           s3_quote_key (CharField): Key for the quote file in S3 bucket.
           status (CharField): Current status of the quote.
           budget (CharField): The budget identifier from which the demand was created.
           corporate_demand_ref (CharField): The corporate identifier for the quote demand.
       """

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
    budget = models.CharField(max_length=50, blank=True, null=True)
    corporate_demand_ref = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.id}"

    def save(self, *args, **kwargs):
        """
        Save the quote instance.

        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: None.

        This method is responsible for saving the quote instance. If the `quote_url` attribute is not set, but `s3_quote_key` is set, it will generate the `quote_url` based on the AWS S3 settings
        """
        # Check if the quote_url is not set and the s3_quote_key is present
        if not self.quote_url and self.s3_quote_key:
            # If so, generate the quote_url using the S3 bucket settings and the s3_quote_key
            self.quote_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.s3_quote_key}'
        # Call the save method of the superclass (Model) to handle the actual saving of the instance
        super(Quote, self).save(*args, **kwargs)


class QuoteItem(models.Model):
    """
    Represents individual items within a quote. Links to both the Quote and Product models.

    Attributes:
        quote (ForeignKey): Link to the Quote model.
        product (ForeignKey): Link to the Product model.
        quantity (PositiveIntegerField): Quantity of the product requested in the quote.
        price (DecimalField): Price of the product. Optional.
    """
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
