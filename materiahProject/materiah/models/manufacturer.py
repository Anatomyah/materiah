from django.db import models
from .supplier import Supplier


class Manufacturer(models.Model):
    """
       Represents a manufacturer in the system.

       This model stores information about manufacturers, including their name and website.
       A manufacturer can have relationships with multiple suppliers.

       Attributes:
       - name (CharField): The name of the manufacturer. This field is unique.
       - website (URLField): The website URL of the manufacturer.
       - suppliers (ManyToManyField): A many-to-many relationship to the 'Supplier' model
         through the 'ManufacturerSupplier' model. This relationship allows the tracking of
         which suppliers are associated with which manufacturers.

       Methods:
       - __str__(self): Returns the manufacturer's name as a string representation of the object.
       """
    name = models.CharField(max_length=255, unique=True)
    website = models.URLField()
    suppliers = models.ManyToManyField('Supplier', through='ManufacturerSupplier')

    def __str__(self):
        return f"{self.name}"


class ManufacturerSupplier(models.Model):
    """
    Intermediate model for the many-to-many relationship between Manufacturer and Supplier.

    This model acts as a through table for the many-to-many relationship between the
    Manufacturer and Supplier models. It explicitly defines the relationship, allowing
    for additional attributes and methods to be added in the future if needed.

    Attributes:
    - manufacturer (ForeignKey): A foreign key to the 'Manufacturer' model, representing the
      manufacturer in the relationship.
    - supplier (ForeignKey): A foreign key to the 'Supplier' model, representing the supplier
      in the relationship.
    """
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
