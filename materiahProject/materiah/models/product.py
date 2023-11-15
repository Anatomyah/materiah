from django.db import models
from django.conf import settings

from .file import FileUploadStatus
from .manufacturer import Manufacturer
from .supplier import Supplier


class Product(models.Model):
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
    volume = models.PositiveIntegerField()
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
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    s3_image_key = models.CharField(max_length=255)
    image_url = models.URLField(max_length=1024, editable=False, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if not self.image_url:
            self.image_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.s3_image_key}'
        super(ProductImage, self).save(*args, **kwargs)


class ProductOrderStatistics(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    order_count = models.IntegerField(default=0)
    last_ordered = models.DateTimeField(null=True, blank=True)
    avg_order_time = models.DurationField(null=True, blank=True)


class OrderNotifications(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255, null=True, blank=True)
    product_cat_num = models.CharField(max_length=255, null=True, blank=True)
    supplier_name = models.CharField(max_length=255, null=True, blank=True)
    current_stock = models.CharField(max_length=255, null=True, blank=True)
    last_ordered = models.DateField(null=True, blank=True)
    avg_order_time = models.CharField(max_length=255, null=True, blank=True)
