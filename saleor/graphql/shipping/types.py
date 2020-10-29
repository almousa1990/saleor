import graphene
from graphene import relay
from collections import defaultdict
from ...core.weight import convert_weight_to_default_weight_unit
from ...shipping import models
from ...warehouse import models as warehouse_models
from ..core.connection import CountableDjangoObjectType, CountableConnection
from ..core.types import CountryDisplay, MoneyRange
from ..core.fields import PrefetchingConnectionField

from ..translations.fields import TranslationField
from ..translations.types import ShippingMethodTranslation
from ..warehouse.types import Warehouse
from ..product.types import ProductVariant, Product
from .enums import ShippingMethodTypeEnum
from django.db.models import Count, Sum
from .dataloaders import CountryByShippingCountryIdLoader, ProvincesByShippingCountryIdLoader
from django.db.models import Prefetch


class ShippingProvince(graphene.ObjectType):
    code = graphene.String(description="The code of this province.")
    name = graphene.String(description="The name of the province.")
    class Meta:
        description = (
            "A province/region within a country"
        )


class ShippingCountry(graphene.ObjectType):
    code = graphene.String(description="The ISO 3166-1 alpha-2 country code of this country and a flag indicating Rest Of World.")
    name = graphene.String(description="The name of the country.")
    provinces = graphene.List(ShippingProvince, description="The provinces/regions associated with this country.")


    class Meta:
        description = (
            "A country that is used to define a zone."
        )
        model = models.ShippingCountry
        interfaces = [relay.Node]
        only_fields = [
            "id",
        ]

    @staticmethod
    def resolve_name(root: models.ShippingCountry, info, **kwargs):
        return CountryByShippingCountryIdLoader(info.context).load(root.id)

    @staticmethod
    def resolve_provinces(root: models.ShippingCountry, info, **kwargs):
        return ProvincesByShippingCountryIdLoader(info.context).load(root.id)





class ShippingMethod(CountableDjangoObjectType):
    type = ShippingMethodTypeEnum(description="Type of the shipping method.")
    translation = TranslationField(
        ShippingMethodTranslation, type_name="shipping method"
    )

    class Meta:
        description = (
            "Shipping method are the methods you'll use to get customer's orders to "
            "them. They are directly exposed to the customers."
        )
        model = models.ShippingMethod
        interfaces = [relay.Node]
        only_fields = [
            "id",
            "maximum_order_price",
            "maximum_order_weight",
            "minimum_order_price",
            "minimum_order_weight",
            "name",
            "price",
        ]

    @staticmethod
    def resolve_maximum_order_weight(root: models.ShippingMethod, *_args):
        return convert_weight_to_default_weight_unit(root.maximum_order_weight)

    @staticmethod
    def resolve_minimum_order_weight(root: models.ShippingMethod, *_args):
        return convert_weight_to_default_weight_unit(root.minimum_order_weight)


class ShippingZone(CountableDjangoObjectType):
    price_range = graphene.Field(
        MoneyRange, description="Lowest and highest prices for the shipping."
    )
    countries = graphene.List(
        ShippingCountry, description="List of countries available for the method."
    )
    shipping_methods = graphene.List(
        ShippingMethod,
        description=(
            "List of shipping methods available for orders"
            " shipped to countries within this shipping zone."
        ),
    )
    class Meta:
        description = (
            "Represents a shipping zone in the shop. Zones are the concept used only "
            "for grouping shipping methods in the dashboard, and are never exposed to "
            "the customers directly."
        )
        model = models.ShippingZone
        interfaces = [relay.Node]
        only_fields = ["id", "name"]

    @staticmethod
    def resolve_price_range(root: models.ShippingZone, *_args):
        return root.price_range

    @staticmethod
    def resolve_countries(root: models.ShippingZone, info, **kwargs):
        return root.countries.all()

    @staticmethod
    def resolve_shipping_methods(root: models.ShippingZone, *_args):
        return root.shipping_methods.all()

class ShippingProfileWarehouseGroup(CountableDjangoObjectType):
    warehouses = graphene.List(
        Warehouse, description="List of active locations that are part of this location group."
    )
    shipping_zones = graphene.List(
        ShippingZone, description="The applicable zones associated to a warehouse group and delivery profile.."
    )
    class Meta:
        description = (
            "Links a warehouse group with zones associated to a shipping profile."

        )
        model = models.ShippingProfileWarehouseGroup
        interfaces = [relay.Node]
        only_fields = ["id"]

    @staticmethod
    def resolve_warehouses(root: models.ShippingProfileWarehouseGroup, *_args):
        return root.warehouses.all()

    @staticmethod
    def resolve_shipping_zones(root: models.ShippingProfileWarehouseGroup, info, first=None, **kwargs):
        return root.shipping_zones.all()



class ShippingProfile(CountableDjangoObjectType):
    profile_warehouse_groups = graphene.List(
        ShippingProfileWarehouseGroup, description="List of shipping zone for shipping profile."
    )
    products = PrefetchingConnectionField(
        Product, description="List of products for shipping profile."
    )
    warehouses_without_rates_count = graphene.Int(description="The number of warehouses without methods defined.")

    unassigned_warehouses = graphene.List(Warehouse, description="List of warehouses that have not been assigned to a warehouse group for this profile.")
    
    origin_warehouse_count = graphene.Int(description="The number of active origin warehouses for the profile.")
    active_shipping_method_count = graphene.Int(description="The number of active shipping methods for the profile.")

    shipping_country_count = graphene.Int(description="The number of countries with active rates to deliver to.")

    class Meta:
        description = (
            "Represents a shipping profile in the shop. Profiles are the concept used only "
            "for grouping products with shipping zones in the dashboard, and are never exposed to "
            "the customers directly."
        )
        model = models.ShippingProfile
        interfaces = [relay.Node]
        only_fields = ["default", "id", "name"]

    @staticmethod
    def resolve_profile_warehouse_groups(root: models.ShippingProfile, *_args):
        return root.warehouse_groups.all()

    @staticmethod
    def resolve_products(root: models.ShippingProfile, info, first=None, **kwargs):
        return root.products.all()

    @staticmethod
    def resolve_warehouses_without_rates_count(root: models.ShippingProfile, *_args):
        query_set = root.warehouse_groups.prefetch_related(Prefetch('shipping_zones', models.ShippingZone.objects.filter(shipping_methods=None))).filter(shipping_zones=None)
        if query_set.exists():
            return query_set.annotate(no_warehouses=Count('warehouses')).aggregate(sum=Sum('no_warehouses')).get('sum')
        else:
            return 0

    @staticmethod
    def resolve_unassigned_warehouses(root: models.ShippingProfile, *_args):
        return warehouse_models.Warehouse.objects.exclude(shipping_profile_warehouse_groups__pk__in=root.warehouse_groups.all().values_list('id', flat=True))

    @staticmethod
    def resolve_origin_warehouse_count(root: models.ShippingProfile, *_args):
        query_set = root.warehouse_groups.prefetch_related(Prefetch('shipping_zones', models.ShippingZone.objects.exclude(shipping_methods=None))).exclude(shipping_zones=None)
        if query_set.exists():
            return query_set.annotate(no_warehouses=Count('warehouses')).aggregate(sum=Sum('no_warehouses')).get('sum')
        else:
            return 0

    @staticmethod
    def resolve_active_shipping_method_count(root: models.ShippingProfile, *_args):
        query_set = models.ShippingMethod.objects.filter(shipping_zone__shipping_profile_warehouse_group__shipping_profile__pk=root.pk)
        return query_set.count()


    @staticmethod
    def resolve_shipping_country_count(root: models.ShippingProfile, *_args):
        query_set = models.ShippingCountry.objects.filter(shipping_zone__shipping_profile_warehouse_group__shipping_profile__pk=root.pk)
        return query_set.count()
