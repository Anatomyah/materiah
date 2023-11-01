# Generated by Django 4.2.1 on 2023-10-18 09:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('materiah', '0029_productorderstatistics_order_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderNotifications',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='materiah.product')),
            ],
        ),
    ]
