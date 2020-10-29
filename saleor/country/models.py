from django.db import models


class Country(models.Model):

    name = models.CharField(max_length=128)

    code = models.CharField(max_length=2, db_index=True)


    display_order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ('display_order', 'name',)

    def __str__(self):
        return self.name

class CountryTranslation(models.Model):
    language_code = models.CharField(max_length=10)
    name = models.CharField(max_length=128, null=True, blank=True)
    country = models.ForeignKey(
        Country, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("language_code", "country", "pk")
        unique_together = (("language_code", "country"),)


class Province(models.Model):
    
    name = models.CharField(max_length=128, db_index=True)
    code = models.CharField(max_length=6)

    display_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    country = models.ForeignKey(Country, related_name="provinces", on_delete=models.CASCADE)

    class Meta:
        ordering = ('-display_order', 'name',)

    def __str__(self):
        return self.name

class ProvinceTranslation(models.Model):
    language_code = models.CharField(max_length=10)
    name = models.CharField(max_length=128, null=True, blank=True)
    province = models.ForeignKey(
        Province, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("language_code", "province", "pk")
        unique_together = (("language_code", "province"),)

