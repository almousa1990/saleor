# Generated by Django 3.1 on 2020-08-28 21:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0128_auto_20200828_2105'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='tags',
        ),
    ]
