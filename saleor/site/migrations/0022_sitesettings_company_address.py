# Generated by Django 2.2.1 on 2019-06-17 13:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0027_customerevent"),
        ("site", "0021_auto_20190326_0521"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="company_address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="address.Address",
            ),
        )
    ]
