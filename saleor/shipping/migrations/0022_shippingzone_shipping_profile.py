# Generated by Django 3.1 on 2020-10-03 20:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0021_auto_20201003_2052'),
    ]

    operations = [
        migrations.AddField(
            model_name='shippingzone',
            name='shipping_profile',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='shipping.shippingprofile'),
            preserve_default=False,
        ),
    ]
