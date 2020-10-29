import django_filters

from ...country.models import Country
from ..core.types import FilterInputObjectType
from ..utils.filters import filter_by_query_param


def filter_country_search(qs, _, value):
    country_fields = ["code", "name"]
    qs = filter_by_query_param(qs, value, country_fields)
    return qs


class CountryFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method=filter_country_search)

    class Meta:
        model = Country
        fields = ["search"]


class CountryFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = CountryFilter
