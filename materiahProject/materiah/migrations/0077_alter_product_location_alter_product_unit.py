# Generated by Django 4.2.7 on 2024-04-17 14:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0076_alter_product_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='location',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='exact location'),
        ),
        migrations.AlterField(
            model_name='product',
            name='unit',
            field=models.CharField(choices=[('L', 'Litres, l'), ('ML', 'Milliliters, ml'), ('UL', 'Microliters, ml'), ('KG', 'Kilograms, kg'), ('G', 'Grams, g'), ('MG', 'Milligrams, mg'), ('UG', 'Micrograms, µg'), ('Package', 'Package'), ('Box', 'Box')], max_length=50, verbose_name='measurement unit'),
        ),
    ]