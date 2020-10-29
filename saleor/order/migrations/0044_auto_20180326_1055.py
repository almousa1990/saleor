# Generated by Django 2.0.3 on 2018-03-26 15:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0008_auto_20180108_0814"),
        ("order", "0043_auto_20180322_0655"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="shipping_method",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="shipping.ShippingMethodCountry",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="billing_address",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="address.Address",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name="order",
            name="shipping_address",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="address.Address",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("unfulfilled", "Unfulfilled"),
                    ("partially fulfilled", "Partially fulfilled"),
                    ("fulfilled", "Fulfilled"),
                    ("canceled", "Canceled"),
                ],
                default="unfulfilled",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="user_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
    ]
