# Generated by Django 4.2.1 on 2023-08-21 11:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('materiah', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='phone',
            new_name='phone_suffix',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_prefix',
            field=models.CharField(
                choices=[('050', '050'), ('051', '051'), ('052', '052'), ('053', '053'), ('054', '054'), ('055', '055'),
                         ('056', '056'), ('058', '058'), ('059', '059')], default='050', max_length=3),
        ),
    ]
