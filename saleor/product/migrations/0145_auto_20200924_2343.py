# Generated by Django 3.1 on 2020-09-24 23:43

from django.db import migrations
import django_measurement.models
import measurement.measures.mass
import saleor.core.weight


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0144_auto_20200917_2009'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productvariant',
            name='weight',
            field=django_measurement.models.MeasurementField(default=saleor.core.weight.zero_weight, measurement=measurement.measures.mass.Mass),
        ),
    ]
