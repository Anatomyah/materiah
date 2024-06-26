from django.db import models
from django.conf import settings

from .manufacturer import Manufacturer
from .supplier import Supplier


class Product(models.Model):
    """Product class for managing products in a database.

    Attributes:
        CATEGORIES (list): List of available categories for products.
        UNITS (list): List of available measurement units for products.
        STORAGE (list): List of available storage conditions for products.
        CURRENCY (list): List of available currencies for products.

    Attributes:
        cat_num (CharField): The catalogue number of the product. Max length: 255. [db_index=True, unique=True]
        name (CharField): The name of the product. Max length: 255. [db_index=True]
        category (CharField): The category of the product. Max length: 255. [choices=CATEGORIES]
        unit (CharField): The measurement unit of the product. Max length: 50. [choices=UNITS]
        unit_quantity (DecimalField): The quantity of the measurement unit. Max digits: 10,
         Decimal places: 4. [null=True, blank=True]
        units_per_sub_unit (PositiveIntegerField): Number of units per main unit. [null=True, blank=True]
        stock (PositiveIntegerField): The stock of the product. [null=True, blank=True]
        storage (CharField): The storage conditions of the product. Max length: 20. [choices=STORAGE]
        location (CharField): The exact location of the product. Max length: 200. [null=True, blank=True]
        price (DecimalField): The price of the product. Max digits: 10, Decimal places: 2. [null=True, blank=True]
        discount (DecimalField): The discount on the product. Max digits: 4, Decimal places: 2. [null=True, blank=True]
        currency (CharField): The currency of the product. Max length: 20. [choices=CURRENCY, null=True, blank=True]
        previous_price (DecimalField): The previous price of the product. Max digits: 10, Decimal places:
        2. [null=True, blank=True]
        previous_discount (DecimalField): The previous discount on the product. Max digits: 4, Decimal places:
        2. [null=True, blank=True]
        url (URLField): The URL of the product. Max length: 500. [null=True, blank=True]
        manufacturer (ForeignKey): The manufacturer of the product. [on_delete=models.CASCADE, null=True, blank=True]
        supplier (ForeignKey): The supplier of the product. [on_delete=models.CASCADE]
        supplier_cat_item (BooleanField): Indicates if the product is a supplier catalog item. [default=False]
        notes (CharField): Additional notes for the product. Max length: 255. [null=True, blank=True]
    """
    CATEGORIES = [
        ('Matrix', 'Matrix'),
        ('Medium', 'Medium'),
        ('Supplement', 'Supplement'),
        ('Powders', 'Powders'),
        ('Enzyme', 'Enzyme'),
        ('Antibody', 'Antibody'),
        ('Dye', 'Dye'),
        ('Hormone', 'Hormone'),
        ('Medication', 'Medication'),
        ('Antibiotic', 'Antibiotic'),
        ('Kit', 'Kit'),
        ('Plastics', 'Plastics'),
        ('Glassware', 'Glassware'),
        ('Sanitary', 'Sanitary'),
        ('Lab Equipment', 'Lab Equipment'),
    ]

    UNITS = [
        ('L', 'Litres, l'),
        ('ML', 'Milliliters, ml'),
        ('UL', 'Microliters, ml'),
        ('KG', 'Kilograms, kg'),
        ('G', 'Grams, g'),
        ('MG', 'Milligrams, mg'),
        ('UG', 'Micrograms, µg'),
        ('Assays', 'Reactions/Tests/Assays'),
        ('Package', 'Package'),
        ('Box', 'Box')
    ]

    STORAGE = [
        ('+4', '+4'),
        ('-20', '-20'),
        ('-40', '-40'),
        ('-80', '-80'),
        ('Room Temperature', 'Room Temperature'),
        ('Other', 'Other')
    ]

    CURRENCY = [
        ('NIS', 'NIS'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
    ]

    cat_num = models.CharField('catalogue number', max_length=255, db_index=True, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=255, choices=CATEGORIES)
    unit = models.CharField('measurement unit', max_length=50, choices=UNITS)
    unit_quantity = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    units_per_sub_unit = models.PositiveIntegerField(null=True, blank=True,
                                                     help_text="Number of units per main unit(Example: 10 packages "
                                                               "per a main unit of a single box)")
    stock = models.PositiveIntegerField(null=True, blank=True)
    storage = models.CharField('storage conditions', max_length=20,
                               choices=STORAGE)
    location = models.CharField('exact location', max_length=200, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    currency = models.CharField('currency', max_length=20, choices=CURRENCY, null=True, blank=True)
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    previous_discount = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    url = models.URLField(max_length=500, null=True, blank=True)
    manufacturer = models.ForeignKey(to=Manufacturer, on_delete=models.CASCADE, null=True, blank=True)
    supplier = models.ForeignKey(to=Supplier, on_delete=models.CASCADE)
    supplier_cat_item = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Overridden save method to update item stock for related ProductItems.
        """
        super().save(*args, **kwargs)
        for item in self.stockitem_set.all():
            item.item_sub_stock = self.unit_quantity
            item.save()

    def __str__(self):
        return f"{self.cat_num}"

    class Meta:
        unique_together = ('cat_num', 'supplier_cat_item')


class StockItem(models.Model):
    """
    Represents a product stock item of a given product.

    Attributes:
        product (ForeignKey): The product associated with the item.
        order_item (ForeignKey): The order item associated with the item. Can be null or blank.
        batch (CharField): The batch number of the item. Can be null or blank.
        in_use (BooleanField): Indicates if the item is currently in use.
        expiry (DateField): The expiry date of the item. Can be null or blank.
        opened_on (DateField): The date the item was opened. Can be null or blank.
        item_sub_stock (PositiveIntegerField): The stock level of the item, initialized based on the product's units per main unit.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, default=None, null=True, blank=True)
    batch = models.CharField(max_length=50, blank=True, null=True)
    in_use = models.BooleanField(default=False)
    expiry = models.DateField(blank=True, null=True)
    opened_on = models.DateField(blank=True, null=True)
    item_sub_stock = models.PositiveIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Overridden save method to automatically set the item sub stock based on the product's units per main unit.
        """
        if not self.id:  # Checking if this is a new instance being created
            if self.product.units_per_sub_unit:
                self.item_sub_stock = self.product.unit_quantity
        super(StockItem, self).save(*args, **kwargs)

    def __str__(self):
        return f"Product Item for {self.product.name}, Batch: {self.batch}"


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
    - avg_order_quantity (DecimalField): The average quantity ordered. Can be null or blank.
    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    order_count = models.IntegerField(default=0)
    last_ordered = models.DateTimeField(null=True, blank=True)
    avg_order_time = models.DurationField(null=True, blank=True)
    avg_order_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class OrderNotifications(models.Model):
    """

    The `OrderNotifications` class is a model that represents order notifications. It is defined in the `models` module.

    Attributes:
        product (OneToOneField): The product associated with the order notification.

    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE)


class ExpiryNotifications(models.Model):
    """
       Class representing expiry notifications for product items.

       Each product item can only have one expiry notification associated with it.

       Attributes:
           stock_item (OneToOneField): The stock item associated with the expiry notification.
       """
    stock_item = models.OneToOneField(StockItem, on_delete=models.CASCADE)

    def __str__(self):
        return f"Expiry notification for {self.stock_item}"
