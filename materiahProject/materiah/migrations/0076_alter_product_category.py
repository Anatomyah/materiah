# Generated by Django 4.2.7 on 2024-04-17 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0075_product_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(choices=[('Matrix', 'Matrix'), ('Medium', 'Medium'), ('Supplement', 'Supplement'), ('Powder', 'Powder'), ('Enzyme', 'Enzyme'), ('Antibody', 'Antibody'), ('Dye', 'Dye'), ('Hormone', 'Hormone'), ('Medication', 'Medication'), ('Antibiotic', 'Antibiotic'), ('Plastics', 'Plastics'), ('Glassware', 'Glassware'), ('Sanitary', 'Sanitary'), ('Lab Equipment', 'Lab Equipment')], max_length=255),
        ),
    ]
