# Generated by Django 4.2.7 on 2024-05-15 09:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0086_productitem_item_stock'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='units_per_main_unit',
            new_name='units_per_sub_unit',
        ),
    ]
