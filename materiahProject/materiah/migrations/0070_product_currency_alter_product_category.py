# Generated by Django 4.2.7 on 2024-01-31 15:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0069_remove_orderitem_expiry'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='currency',
            field=models.CharField(blank=True, choices=[('NIS', 'NIS'), ('USD', 'USD'), ('EUR', 'EUR')], max_length=20, null=True, verbose_name='currency'),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(choices=[('Medium', 'Medium'), ('Powders', 'Powders'), ('Enzymes', 'Enzymes'), ('Plastics', 'Plastics'), ('Glassware', 'Glassware'), ('Sanitary', 'Sanitary'), ('Lab Equipment', 'Lab Equipment'), ('Antibodies', 'Antibodies')], max_length=255),
        ),
    ]
