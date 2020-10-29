import django_filters

from ...theme.models import Theme
from ..core.types import FilterInputObjectType
from ..utils.filters import filter_by_query_param


def filter_theme_search(qs, _, value):
    theme_fields = ["slug", "name"]
    qs = filter_by_query_param(qs, value, theme_fields)
    return qs


class ThemeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method=filter_theme_search)

    class Meta:
        model = Theme
        fields = ["search"]


class ThemeFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = ThemeFilter
