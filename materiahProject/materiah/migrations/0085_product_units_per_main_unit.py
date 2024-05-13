# Generated by Django 4.2.7 on 2024-05-13 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0084_order_corporate_order_ref_quote_budget_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='units_per_main_unit',
            field=models.PositiveIntegerField(blank=True, help_text='Number of units per main unit(Example: 10 packages per a main unit of a single box)', null=True),
        ),
    ]
