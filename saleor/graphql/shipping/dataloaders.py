from collections import defaultdict
from ..country.dataloaders import CountryByCodeLoader, ProvinceByCodeLoader
from ...shipping.models import ShippingCountry
from ..core.dataloaders import DataLoader


class CountryByShippingCountryIdLoader(DataLoader):
    context_key = "country_by_shippingcountry"

    def batch_load(self, keys):
        shippingcountry_country_pairs = list(
            ShippingCountry.objects.filter(pk__in=keys)
            .order_by("id")
            .values_list("id", "code")
        )
        shippingcountry_country_map = defaultdict(list)
        for shippingcountry_id, code in shippingcountry_country_pairs:
            shippingcountry_country_map[shippingcountry_id] = code

        def get_data(country):
            return country.name

        def map_countries(countries):
            country_map = {c.code: c for c in countries}
            return [
                get_data(country_map[shippingcountry_country_map[shippingcountry_id]])
                for shippingcountry_id in keys
            ]

        return (
            CountryByCodeLoader(self.context)
            .load_many(set(code for _, code in shippingcountry_country_pairs))
            .then(map_countries)
        )


class ShippingCountriesByShippingZoneIdLoader(DataLoader):
    context_key = "countries_by_shippingzone"

    def batch_load(self, keys):
        zone_country_pairs = list(
            ShippingCountry.objects.filter(shipping_zone_id__in=keys)
            .order_by("id")
            .values_list("shipping_zone_id", "id", "code")
        )
        zone_country_map = defaultdict(list)
        for zid, cid, code in zone_country_pairs:
            zone_country_map[zid].append(code)

        country_country_map = defaultdict(list)

        for zid, cid, code in zone_country_pairs:
            country_country_map[code] = cid

        def append_pk(country):
            shipping_country_id = country_country_map[country.code]
            return {'id': shipping_country_id, 'code': country.code, 'name': country.name}

        def map_countries(countries):
            country_map = {c.code: c for c in countries}
            return [
                [append_pk(country_map[code]) for code in zone_country_map[zid]]
                for zid in keys
            ]

        return (
            CountryByCodeLoader(self.context)
            .load_many(set(code for zid, cid, code in zone_country_pairs))
            .then(map_countries)
        )



class ProvincesByShippingCountryIdLoader(DataLoader):
    context_key = "provinces_by_shippingcountries"

    def batch_load(self, keys):
        country_province_pairs = ShippingCountry.objects.filter(pk__in=keys).order_by(
            "id").values_list("id", "provinces").values_list("id", "provinces")

        country_province_map = defaultdict(list)
        all_provinces = []
        for cid, provinces in country_province_pairs:
            country_province_map[cid] = provinces
            all_provinces += provinces

        def map_provinces(provinces):
            province_map = {c.code: c for c in provinces}
            return [
                [province_map[code] for code in country_province_map[cid]]
                for cid in keys
            ]

        return (
            ProvinceByCodeLoader(self.context)
            .load_many(set(all_provinces))
            .then(map_provinces)
        )
