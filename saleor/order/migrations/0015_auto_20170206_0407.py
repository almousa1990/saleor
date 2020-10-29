# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-06 10:07
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("order", "0014_auto_20161028_0955")]

    operations = [
        migrations.AlterModelOptions(
            name="deliverygroup",
            options={
                "verbose_name": "Delivery Group",
                "verbose_name_plural": "Delivery Groups",
            },
        ),
        migrations.AlterModelOptions(
            name="order",
            options={
                "ordering": ("-last_status_change",),
                "verbose_name": "Order",
                "verbose_name_plural": "Orders",
            },
        ),
        migrations.AlterModelOptions(
            name="ordereditem",
            options={
                "verbose_name": "Ordered item",
                "verbose_name_plural": "Ordered items",
            },
        ),
        migrations.AlterModelOptions(
            name="orderhistoryentry",
            options={
                "ordering": ("date",),
                "verbose_name": "Order history entry",
                "verbose_name_plural": "Order history entries",
            },
        ),
        migrations.AlterModelOptions(
            name="ordernote",
            options={
                "verbose_name": "Order note",
                "verbose_name_plural": "Order notes",
            },
        ),
        migrations.AlterModelOptions(
            name="payment",
            options={
                "ordering": ("-pk",),
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
            },
        ),
        migrations.AlterField(
            model_name="deliverygroup",
            name="last_updated",
            field=models.DateTimeField(
                auto_now=True, null=True, verbose_name="last updated"
            ),
        ),
        migrations.AlterField(
            model_name="deliverygroup",
            name="shipping_method_name",
            field=models.CharField(
                blank=True,
                default=None,
                editable=False,
                max_length=255,
                null=True,
                verbose_name="shipping method name",
            ),
        ),
        migrations.AlterField(
            model_name="deliverygroup",
            name="tracking_number",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="tracking number"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="billing_address",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="address.Address",
                verbose_name="billing address",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="discount_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="discount amount",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="discount_name",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="discount name"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="shipping_address",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="address.Address",
                verbose_name="shipping address",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="total_net",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="total net",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="total_tax",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="total tax",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="tracking_client_id",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=36,
                verbose_name="tracking client id",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="user_email",
            field=models.EmailField(
                blank=True,
                default="",
                editable=False,
                max_length=254,
                verbose_name="user email",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="voucher",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="discount.Voucher",
                verbose_name="voucher",
            ),
        ),
        migrations.AlterField(
            model_name="ordereditem",
            name="delivery_group",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="order.DeliveryGroup",
                verbose_name="delivery group",
            ),
        ),
        migrations.AlterField(
            model_name="ordereditem",
            name="stock",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="product.Stock",
                verbose_name="stock",
            ),
        ),
        migrations.AlterField(
            model_name="orderhistoryentry",
            name="comment",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="comment"
            ),
        ),
        migrations.AlterField(
            model_name="orderhistoryentry",
            name="order",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="history",
                to="order.Order",
                verbose_name="order",
            ),
        ),
        migrations.AlterField(
            model_name="orderhistoryentry",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
                verbose_name="user",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="order",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="order.Order",
                verbose_name="order",
            ),
        ),
    ]
