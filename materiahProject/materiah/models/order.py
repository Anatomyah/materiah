from django.db import models

from materiah.models.quote import Quote, QuoteItem


class Order(models.Model):
    quote = models.OneToOneField(to=Quote, on_delete=models.SET_NULL, null=True)
    arrival_date = models.DateField()
    received_by = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f"{self.id}"


class OrderItem(models.Model):
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
    batch = models.CharField(max_length=50, blank=True, null=True)
    expiry = models.DateField(blank=True, null=True)
    status = models.CharField('status', max_length=22,
                              choices=STATUS_CHOICES, default='OK')
    issue_detail = models.CharField(max_length=250, null=True)


class OrderImage(models.Model):
    product = models.ForeignKey(Order, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='orders/')
    alt_text = models.CharField(max_length=255, blank=True)
