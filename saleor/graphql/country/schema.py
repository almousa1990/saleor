import graphene

from ..core.fields import FilterInputConnectionField
from .filters import CountryFilterInput
from .resolvers import resolve_country, resolve_countries
from .types import Country


class CountryQueries(graphene.ObjectType):
    country = graphene.Field(
        Country,
        code=graphene.String(description="The slug of the page."),
        description="Look up a country by slug.",
    )
    countries = FilterInputConnectionField(
        Country,
        filter=CountryFilterInput(description="Filtering options for countries."),
        description="List of countries.",
    )

    def resolve_country(self, info, code=None):
        return resolve_country(info, code)

    def resolve_countries(self, info, **kwargs):
        return resolve_countries(info, **kwargs)
