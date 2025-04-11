# Generated by Django 5.1.6 on 2025-02-27 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_alter_product_min_stock_alter_product_product_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movement',
            name='movement_type',
            field=models.CharField(choices=[('استلام', 'استلام'), ('سحب', 'سحب')], max_length=10),
        ),
        migrations.AlterField(
            model_name='product',
            name='min_stock',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='product',
            name='product_name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='product',
            name='quantity',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='product',
            name='unit',
            field=models.CharField(max_length=20),
        ),
    ]
