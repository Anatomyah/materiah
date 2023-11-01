from django.db import models

from materiah.models.product import Product
from materiah.models.supplier import Supplier


class Quote(models.Model):
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
    quote_file = models.FileField(upload_to='quotes_pdfs/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')

    def __str__(self):
        return f"{self.id}"


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
