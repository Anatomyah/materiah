# Generated by Django 4.2.1 on 2023-10-01 08:25

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('materiah', '0020_quote_fufilled'),
    ]

    operations = [
        migrations.RenameField(
            model_name='quote',
            old_name='fufilled',
            new_name='fulfilled',
        ),
    ]
