# Generated by Django 4.2.1 on 2023-08-22 06:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('materiah', '0005_quote_pdf_images'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Images',
            new_name='ProductImage',
        ),
    ]
