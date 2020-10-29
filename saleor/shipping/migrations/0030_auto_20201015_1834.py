# Generated by Django 3.1 on 2020-10-15 18:34

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0029_auto_20201012_1755'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shippingzone',
            name='countries',
        ),
        migrations.CreateModel(
            name='ShippingCountry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country', models.CharField(max_length=2)),
                ('zones', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=10), size=None)),
                ('shipping_zone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='countries', to='shipping.shippingzone')),
            ],
            options={
                'permissions': (('manage_shipping', 'Manage shipping.'),),
            },
        ),
    ]
