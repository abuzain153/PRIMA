# Generated by Django 5.2 on 2025-05-08 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_product_formatted_min_stock_display_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productwarehouse',
            name='quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
