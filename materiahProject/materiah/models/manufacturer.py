from django.db import models

from .supplier import Supplier


class Manufacturer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    website = models.URLField()
    suppliers = models.ManyToManyField('Supplier', through='ManufacturerSupplier')

    def __str__(self):
        return f"{self.name}"


class ManufacturerSupplier(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
