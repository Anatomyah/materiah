# Generated by Django 4.2.1 on 2023-09-01 07:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('materiah', '0006_rename_images_productimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
    ]
