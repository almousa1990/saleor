from ...country.models import Country, Province
from ..core.dataloaders import DataLoader


class CountryByCodeLoader(DataLoader):
    context_key = "country_by_code"

    def batch_load(self, keys):
        countries = Country.objects.filter(code__in=keys).all()
        return [countries.get(code=code) for code in keys]


class ProvinceByCodeLoader(DataLoader):
    context_key = "province_by_code"

    def batch_load(self, keys):
        provinces = Province.objects.filter(code__in=keys).all()
        return [provinces.get(code=code) for code in keys]
