# Generated by Django 3.1 on 2020-10-05 17:45

from django.db import migrations, models
import django_countries.fields
import saleor.address.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=256)),
                ('last_name', models.CharField(blank=True, max_length=256)),
                ('company_name', models.CharField(blank=True, max_length=256)),
                ('street_address_1', models.CharField(blank=True, max_length=256)),
                ('street_address_2', models.CharField(blank=True, max_length=256)),
                ('city', models.CharField(blank=True, max_length=256)),
                ('city_area', models.CharField(blank=True, max_length=128)),
                ('postal_code', models.CharField(blank=True, max_length=20)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('country_area', models.CharField(blank=True, max_length=128)),
                ('phone', saleor.address.models.PossiblePhoneNumberField(blank=True, default='', max_length=128, region=None)),
            ],
            options={
                'ordering': ('pk',),
            },
        ),
    ]
