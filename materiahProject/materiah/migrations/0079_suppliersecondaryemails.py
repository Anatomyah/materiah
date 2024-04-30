# Generated by Django 4.2.7 on 2024-04-24 09:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0078_alter_product_unit_quantity'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupplierSecondaryEmails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='emails', to='materiah.supplier')),
            ],
        ),
    ]
