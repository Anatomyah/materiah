# Generated by Django 4.2.7 on 2023-11-14 08:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0051_quoteitem_previous_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quoteitem',
            name='previous_price',
        ),
        migrations.AddField(
            model_name='product',
            name='previous_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
