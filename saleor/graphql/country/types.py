from graphene import relay
import graphene
from ...country import models
from ..core.connection import CountableDjangoObjectType
from ..translations.fields import TranslationField
from ..translations.types import BaseTranslationType

class ProvinceTranslation(BaseTranslationType):
    class Meta:
        model = models.ProvinceTranslation
        interfaces = [relay.Node]
        only_fields = [
            "name",
        ]

class Province(CountableDjangoObjectType):
    translation = TranslationField(ProvinceTranslation, type_name="country")

    class Meta:
        description = (
            "A country province/region"
        )
        only_fields = [
            "name",
            "code",
        ]
        interfaces = [relay.Node]
        model = models.Province


class CountryTranslation(BaseTranslationType):
    class Meta:
        model = models.CountryTranslation
        interfaces = [relay.Node]
        only_fields = [
            "name",
        ]

class Country(CountableDjangoObjectType):
    provinces = graphene.List(
            Province, description="List of province in country."
        )
    translation = TranslationField(CountryTranslation, type_name="country")

    class Meta:
        description = (
            "A country available in the shop "
        )
        only_fields = [
            "name",
            "code",
            "id",
        ]
        interfaces = [relay.Node]
        model = models.Country

    @staticmethod
    def resolve_provinces(root: models.Country, _info):
        return root.provinces.all()
