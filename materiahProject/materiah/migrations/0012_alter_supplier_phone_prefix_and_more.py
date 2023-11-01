# Generated by Django 4.2.1 on 2023-09-04 12:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('materiah', '0011_remove_userprofile_id_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplier',
            name='phone_prefix',
            field=models.CharField(
                choices=[('050', '050'), ('051', '051'), ('052', '052'), ('053', '053'), ('054', '054'), ('055', '055'),
                         ('056', '056'), ('058', '058'), ('059', '059'), ('02', '02'), ('03', '03'), ('04', '04'),
                         ('05', '05'), ('08', '08'), ('09', '09'), ('071', '071'), ('072', '072'), ('073', '073'),
                         ('074', '074'), ('076', '076'), ('077', '077'), ('079', '079')], default='02', max_length=3),
        ),
        migrations.AlterField(
            model_name='supplieruserprofile',
            name='contact_phone_prefix',
            field=models.CharField(blank=True, choices=[('050', '050'), ('051', '051'), ('052', '052'), ('053', '053'),
                                                        ('054', '054'), ('055', '055'), ('056', '056'), ('058', '058'),
                                                        ('059', '059'), ('02', '02'), ('03', '03'), ('04', '04'),
                                                        ('05', '05'), ('08', '08'), ('09', '09'), ('071', '071'),
                                                        ('072', '072'), ('073', '073'), ('074', '074'), ('076', '076'),
                                                        ('077', '077'), ('079', '079')], default='050', max_length=3,
                                   null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_prefix',
            field=models.CharField(
                choices=[('050', '050'), ('051', '051'), ('052', '052'), ('053', '053'), ('054', '054'), ('055', '055'),
                         ('056', '056'), ('058', '058'), ('059', '059'), ('02', '02'), ('03', '03'), ('04', '04'),
                         ('05', '05'), ('08', '08'), ('09', '09'), ('071', '071'), ('072', '072'), ('073', '073'),
                         ('074', '074'), ('076', '076'), ('077', '077'), ('079', '079')], default='050', max_length=3),
        ),
    ]
