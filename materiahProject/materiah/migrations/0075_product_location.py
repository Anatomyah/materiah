# Generated by Django 4.2.7 on 2024-04-16 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0074_userprofile_gmail_configured'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='location',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='exact location'),
        ),
    ]
