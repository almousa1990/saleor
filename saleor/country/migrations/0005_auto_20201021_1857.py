# Generated by Django 3.1 on 2020-10-21 18:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0004_auto_20201019_2255'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='country',
            options={'ordering': ('display_order', 'name')},
        ),
    ]
