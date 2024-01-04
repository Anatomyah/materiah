from django.db import models
from django.conf import settings

from .manufacturer import Manufacturer
from .supplier import Supplier


class Product(models.Model):
    """
        Represents a product in the system.

        This model stores comprehensive details about products, including catalog numbers, names,
        categories, units, volumes, stock levels, storage conditions, pricing, URLs, and
        relationships to manufacturers and suppliers.

        Attributes:
        - cat_num (CharField): The catalog number of the product, used as a unique identifier.
        - name (CharField): The name of the product.
        - category (CharField): The category of the product, chosen from predefined CATEGORIES.
        - unit (CharField): The unit of measurement for the product, chosen from predefined UNITS.
        - unit_quantity (PositiveIntegerField): The volume or quantity of the product.
        - stock (PositiveIntegerField): The current stock level of the product. Can be null or blank.
        - storage (CharField): Storage conditions for the product, chosen from predefined STORAGE options.
        - price (DecimalField): The current price of the product. Can be null or blank.
        - previous_price (DecimalField): The previous price of the product for price change tracking. Can be null or blank.
        - url (URLField): A URL to more information about the product.
        - manufacturer (ForeignKey): A foreign key to the 'Manufacturer' model.
        - supplier (ForeignKey): A foreign key to the 'Supplier' model.
        - supplier_cat_item (BooleanField): A flag to indicate whether the product is a supplier catalog item.

        Constants:
        - CATEGORIES (list): Predefined product categories.
        - UNITS (list): Predefined units of measurement for products.
        - STORAGE (list): Predefined storage conditions.

        Methods:
        - __str__(self): Returns the catalog number as a string representation of the product.

        Meta:
        - unique_together: Ensures that each combination of 'cat_num' and 'supplier_cat_item' is unique.
        """
    CATEGORIES = [
        ('Medium', 'Medium'),
        ('Powders', 'Powders'),
        ('Enzymes', 'Enzymes'),
        ('Plastics', 'Plastics'),
        ('Glassware', 'Glassware'),
        ('Sanitary', 'Sanitary'),
        ('Lab Equipment', 'Lab Equipment')
    ]

    UNITS = [
        ('ML', 'Milliliters, ml'),
        ('G', 'Grams, g'),
        ('MG', 'Milligrams, mg'),
        ('UG', 'Micrograms, µg'),
        ('Package', 'Package'),
        ('Box', 'Box')
    ]

    STORAGE = [
        ('+4', '+4'),
        ('-20', '-20'),
        ('-40', '-40'),
        ('-80', '-80'),
        ('Other', 'Other')
    ]

    cat_num = models.CharField('catalogue number', max_length=255, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=255, choices=CATEGORIES)
    unit = models.CharField('measurement unit', max_length=50, choices=UNITS)
    unit_quantity = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(null=True, blank=True)
    storage = models.CharField('storage conditions', max_length=20,
                               choices=STORAGE)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    url = models.URLField()
    manufacturer = models.ForeignKey(to=Manufacturer, on_delete=models.CASCADE)
    supplier = models.ForeignKey(to=Supplier, on_delete=models.CASCADE)
    supplier_cat_item = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.cat_num}"

    class Meta:
        unique_together = ('cat_num', 'supplier_cat_item')


class ProductImage(models.Model):
    """
    Represents an image associated with a product.

    This model stores the S3 key and URL for product images. The image URL is automatically
    generated based on the S3 key if not provided.

    Attributes:
    - product (ForeignKey): A foreign key to the 'Product' model, indicating the product associated with the image.
    - s3_image_key (CharField): The S3 key for the image.
    - image_url (URLField): The URL of the image. This field is automatically populated if blank.
    - alt_text (CharField): Alternative text for the image, used for accessibility and SEO.

    Methods:
    - save(*args, **kwargs): Overridden to automatically set the image_url based on the s3_image_key if not provided.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    s3_image_key = models.CharField(max_length=255)
    image_url = models.URLField(max_length=1024, editable=False, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        """
        Save the ProductImage instance.

        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: None.
        """
        # Check if the image_url is not set
        if not self.image_url:
            # Then auto-construct the image_url using the S3 bucket settings and the image key
            self.image_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.s3_image_key}'
        # Call the superclass' save method to handle the actual saving of the instance
        super(ProductImage, self).save(*args, **kwargs)


class ProductOrderStatistics(models.Model):
    """
    Stores statistical data about product orders.

    This model records order-related statistics for each product, such as the total number of orders,
    date of last order, and average order time.

    Attributes:
    - product (OneToOneField): A one-to-one relationship to the 'Product' model.
    - order_count (IntegerField): The total number of times the product has been ordered.
    - last_ordered (DateTimeField): The date and time when the product was last ordered. Can be null or blank.
    - avg_order_time (DurationField): The average time between orders. Can be null or blank.
    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    order_count = models.IntegerField(default=0)
    last_ordered = models.DateTimeField(null=True, blank=True)
    avg_order_time = models.DurationField(null=True, blank=True)


class OrderNotifications(models.Model):
    """
        The OrderNotifications class is a Django model that represents notifications related to product orders.
        This class is designed to keep track of various details associated with products and their ordering process.
        It is particularly useful for maintaining a record of inventory, supplier details, and order timings.

        Attributes:
            product (OneToOneField): A one-to-one relationship with the Product model. Each instance of OrderNotifications
                is linked to a specific product. The on_delete=models.CASCADE argument ensures that if a Product is deleted,
                the associated OrderNotifications instance is also deleted.
            product_name (CharField): Stores the name of the product. Optional field, can be left blank or set to null.
                Max Length: 255 characters.
            product_cat_num (CharField): Holds the product catalog number, allowing for easy reference. Optional field.
                Max Length: 255 characters.
            supplier_name (CharField): Records the name of the supplier for the product. Optional field.
                Max Length: 255 characters.
            current_stock (CharField): Indicates the current stock level of the product. Optional field.
                Max Length: 255 characters.
            last_ordered (DateField): Captures the date when the product was last ordered. Optional field.
            avg_order_time (CharField): Contains the average time taken for the product to be ordered. Optional field.
                Max Length: 255 characters.

        Usage:
            This model can be utilized in inventory management systems, e-commerce platforms, or any application where
            tracking product order details is essential. It provides a comprehensive view of product-related data, from
            stock levels to supplier information, aiding in efficient inventory control and order planning.
        """
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255, null=True, blank=True)
    product_cat_num = models.CharField(max_length=255, null=True, blank=True)
    supplier_name = models.CharField(max_length=255, null=True, blank=True)
    current_stock = models.CharField(max_length=255, null=True, blank=True)
    last_ordered = models.DateField(null=True, blank=True)
    avg_order_time = models.CharField(max_length=255, null=True, blank=True)
