# Generated by Django 4.2.7 on 2024-05-06 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0082_alter_expirynotifications_product_item'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
