# Generated by Django 4.2.7 on 2024-05-07 07:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0083_alter_product_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='corporate_order_ref',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='quote',
            name='budget',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='quote',
            name='corporate_demand_ref',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
