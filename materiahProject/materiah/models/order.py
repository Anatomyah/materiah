from django.conf import settings
from django.db import models

from .quote import Quote, QuoteItem


class Order(models.Model):
    """
        Represents an order in the system.

        This model stores information about an order, including its association with a quote,
        the expected arrival date, and the recipient of the order.

        Attributes:
        - quote (OneToOneField): A one-to-one relationship to the 'Quote' model. This field can be null,
          allowing for orders that are not directly associated with a quote.
        - arrival_date (DateField): The expected date of arrival for the order.
        - received_by (CharField): The name of the individual who received the order. This field can be null.

        Methods:
        - __str__(self): Returns the order ID as a string representation of the object.
        """
    quote = models.OneToOneField(to=Quote, on_delete=models.PROTECT, null=True)
    arrival_date = models.DateField()
    received_by = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f"{self.id}"


class OrderItem(models.Model):
    """
    Represents an item within an order.

    This model stores details about each item in an order, including the associated quote item,
    quantity, status, and any issue details.

    Attributes:
    - order (ForeignKey): A foreign key to the 'Order' model, representing the order to which the item belongs.
    - quote_item (OneToOneField): A one-to-one relationship to the 'QuoteItem' model. This field can be null.
    - quantity (PositiveIntegerField): The quantity of the item ordered.
    - status (CharField): The status of the item upon receipt, with choices such as 'OK', 'Did not arrive', etc.
    - issue_detail (CharField): Detailed description of any issues with the item. This field can be null.

    Constants:
    - STATUS_CHOICES (list): A list of tuples defining the possible status choices for order items.
    """
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
    status = models.CharField('status', max_length=22,
                              choices=STATUS_CHOICES, default='OK')
    issue_detail = models.CharField(max_length=250, null=True)


class OrderImage(models.Model):
    """
        Represents an image associated with an order.

        This model stores the URL and S3 key for images related to orders. The image URL is
        automatically generated based on the S3 key if not provided.

        Attributes:
        - order (ForeignKey): A foreign key to the 'Order' model, representing the order with which the image is associated.
        - image_url (URLField): The URL of the image. This field is automatically populated if blank.
        - s3_image_key (CharField): The S3 key for the image.

        Methods:
        - save(*args, **kwargs): Overridden to automatically set the image_url based on the s3_image_key if not provided.
        """
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    image_url = models.URLField(max_length=1024, editable=False, blank=True)
    s3_image_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        """
        Save method

        This method saves the current instance of OrderImage.

        :param args: Variable length argument list.
        :param kwargs: Arbitrary keyword arguments.
        :return: None
        """
        # Check if image_url attribute of the OrderImage instance is not set
        if not self.image_url:
            # If it's not set, construct image_url using the settings of AWS S3 bucket and the s3_image_key
            self.image_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.s3_image_key}'
        # Save (or update if it called on an existing instance) the OrderImage instance using the superclass' save method
        super(OrderImage, self).save(*args, **kwargs)
