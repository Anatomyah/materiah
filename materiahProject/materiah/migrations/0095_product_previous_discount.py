# Generated by Django 4.2.7 on 2024-06-25 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0094_quoteitem_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='previous_discount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
    ]
