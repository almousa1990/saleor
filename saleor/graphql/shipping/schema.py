import graphene

from ...core.permissions import ShippingPermissions
from ..core.fields import PrefetchingConnectionField
from ..decorators import permission_required
from ..translations.mutations import ShippingMethodTranslate
from .bulk_mutations import ShippingMethodBulkDelete, ShippingZoneBulkDelete, ShippingProfileBulkDelete
from .mutations import (
    ShippingMethodCreate,
    ShippingMethodDelete,
    ShippingMethodUpdate,
    ShippingZoneCreate,
    ShippingZoneDelete,
    ShippingZoneUpdate,
    ShippingProfileCreate,
    ShippingProfileDelete,
    ShippingProfileUpdate,
    ShippingProfileWarehouseGroupCreate,
    ShippingProfileWarehouseGroupUpdate,
)
from .resolvers import resolve_shipping_methods, resolve_shipping_zones, resolve_shipping_profiles
from .types import ShippingMethod, ShippingZone, ShippingProfile


class ShippingQueries(graphene.ObjectType):
    shipping_method = graphene.Field(
        ShippingMethod,
        id=graphene.Argument(
            graphene.ID, description="ID of the shipping method.", required=True
        ),
        description="Look up a shipping method by ID.",
    )
    shipping_methods = PrefetchingConnectionField(
        ShippingMethod, description="List of the shop's shipping methods."
    )
    shipping_zone = graphene.Field(
        ShippingZone,
        id=graphene.Argument(
            graphene.ID, description="ID of the shipping zone.", required=True
        ),
        description="Look up a shipping zone by ID.",
    )
    shipping_zones = PrefetchingConnectionField(
        ShippingZone, description="List of the shop's shipping zones."
    )
    shipping_profile = graphene.Field(
        ShippingProfile,
        id=graphene.Argument(
            graphene.ID, description="ID of the shipping profile.", required=True
        ),
        description="Look up a shipping profile by ID.",
    )
    shipping_profiles = PrefetchingConnectionField(
        ShippingProfile, description="List of the shop's shipping zones."
    )

    @permission_required(ShippingPermissions.MANAGE_SHIPPING)
    def resolve_shipping_method(self, info, id):
        return graphene.Node.get_node_from_global_id(info, id, ShippingMethod)

    @permission_required(ShippingPermissions.MANAGE_SHIPPING)
    def resolve_shipping_methods(self, info, **_kwargs):
        return resolve_shipping_methods(info)

    @permission_required(ShippingPermissions.MANAGE_SHIPPING)
    def resolve_shipping_zone(self, info, id):
        return graphene.Node.get_node_from_global_id(info, id, ShippingZone)

    @permission_required(ShippingPermissions.MANAGE_SHIPPING)
    def resolve_shipping_zones(self, info, **_kwargs):
        return resolve_shipping_zones(info)

    @permission_required(ShippingPermissions.MANAGE_SHIPPING)
    def resolve_shipping_profile(self, info, id):
        return graphene.Node.get_node_from_global_id(info, id, ShippingProfile)

    #@permission_required(ShippingPermissions.MANAGE_SHIPPING)
    def resolve_shipping_profiles(self, info, **_kwargs):
        return resolve_shipping_profiles(info)

class ShippingMutations(graphene.ObjectType):
    shipping_method_create = ShippingMethodCreate.Field()
    shipping_method_delete = ShippingMethodDelete.Field()
    shipping_method_bulk_delete = ShippingMethodBulkDelete.Field()
    shipping_method_update = ShippingMethodUpdate.Field()
    shipping_method_translate = ShippingMethodTranslate.Field()

    shipping_zone_create = ShippingZoneCreate.Field()
    shipping_zone_delete = ShippingZoneDelete.Field()
    shipping_zone_bulk_delete = ShippingZoneBulkDelete.Field()
    shipping_zone_update = ShippingZoneUpdate.Field()


    shipping_profile_create = ShippingProfileCreate.Field()
    shipping_profile_delete = ShippingProfileDelete.Field()
    shipping_profile_bulk_delete = ShippingProfileBulkDelete.Field()
    shipping_profile_update = ShippingProfileUpdate.Field()

    shipping_profile_warehouse_group_create = ShippingProfileWarehouseGroupCreate.Field()
    shipping_profile_warehouse_group_update = ShippingProfileWarehouseGroupUpdate.Field()