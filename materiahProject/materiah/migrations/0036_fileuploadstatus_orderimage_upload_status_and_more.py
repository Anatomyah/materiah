# Generated by Django 4.2.7 on 2023-11-02 12:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('materiah', '0035_remove_order_receipt_img_orderimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUploadStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('uploading', 'Uploading'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('error_message', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='orderimage',
            name='upload_status',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_image_model', to='materiah.fileuploadstatus'),
        ),
        migrations.AddField(
            model_name='productimage',
            name='upload_status',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='product_image_model', to='materiah.fileuploadstatus'),
        ),
        migrations.AddField(
            model_name='quote',
            name='upload_status',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='quote_model', to='materiah.fileuploadstatus'),
        ),
    ]