from collections import defaultdict
import graphene
from django.core.exceptions import ValidationError
from django.db import transaction

from ...core.permissions import ShippingPermissions
from ...shipping import models
from ..product.types import Product
from ...shipping.error_codes import ShippingErrorCode
from ...shipping.utils import (
    default_shipping_zone_exists,
    get_countries_without_shipping_zone,
)
from ..core.mutations import BaseMutation, ModelDeleteMutation, ModelMutation
from ..core.scalars import Decimal, WeightScalar
from ..core.types.common import ShippingError
from ..core.utils import get_duplicates_ids
from .enums import ShippingMethodTypeEnum
from .types import ShippingMethod, ShippingZone, ShippingProfile


class ShippingMethodInput(graphene.InputObjectType):
    name = graphene.String(description="Name of the shipping method.")
    price = Decimal(description="Shipping price of the shipping method.")
    minimum_order_price = Decimal(
        description="Minimum order price to use this shipping method."
    )
    maximum_order_price = Decimal(
        description="Maximum order price to use this shipping method."
    )
    minimum_order_weight = WeightScalar(
        description="Minimum order weight to use this shipping method."
    )
    maximum_order_weight = WeightScalar(
        description="Maximum order weight to use this shipping method."
    )
    type = ShippingMethodTypeEnum(description="Shipping type: general, price or weight based.")
    shipping_zone = graphene.ID(
        description="Shipping zone this method belongs to.", name="shippingZone"
    )


class ShippingCountryInput(graphene.InputObjectType):
    code = graphene.String(
        description="Shipping country code"
    )
    provinces = graphene.List(
        graphene.String, description="Shipping country provinces"
    )

class ShippingZoneInput(graphene.InputObjectType):
    name = graphene.String(
        description="Shipping zone's name. Visible only to the staff."
    )
    countries = graphene.List(
        ShippingCountryInput, description="List of countries in this shipping zone."
    )
    
    shipping_profile_warehouse_group = graphene.ID(
        description="Shipping profile warehouse group this zone belongs to.", name="shippingProfileWarehouseGroup"
    )


class ShippingProfileCreateInput(graphene.InputObjectType):
    name = graphene.String(
        description="Shipping zone's name. Visible only to the staff."
    )

    add_products = graphene.List(graphene.ID,
        description="List of products to assign to a shipping profile "
    )


class ShippingProfileUpdateInput(ShippingProfileCreateInput):
    remove_products = graphene.List(graphene.ID,
        description="List of products to unassign to a shipping profile"
    )


class ShippingProfileWarehouseGroupCreateInput(graphene.InputObjectType):
    add_warehouses = graphene.List(graphene.ID,
        description="List of warehouses to assign to a shipping profile warehouse group"
    )
    shipping_profile = graphene.ID(
        description="Shipping profile this group belongs to.", name="shippingProfile"
    )


class ShippingProfileWarehouseGroupUpdateInput(ShippingProfileWarehouseGroupCreateInput):
    remove_warehouses = graphene.List(graphene.ID,
        description="List of warehouses to unassign to a shipping profile warehouse group"
    )


class ShippingZoneMixin:
    @classmethod
    def clean_input(cls, info, instance, data, input_cls=None):

        countries = data.get("countries", None)
        if not instance.countries.all() and countries is not None and len(countries)==0:
            raise ValidationError(
                {
                    "countries": ValidationError(
                        "Shipping zone must have countries selected", code=ShippingErrorCode.REQUIRED.value
                    )
                }
            )


        cleaned_input = super().clean_input(info, instance, data)

        return cleaned_input


    @classmethod
    def update_or_create_countries(cls,info,  shipping_zone, cleaned_inputs):
        
        warehouse_group_shipping_zones = shipping_zone.shipping_profile_warehouse_group.shipping_zones.exclude(pk=shipping_zone.pk)
        warehouse_group_countries = sum([list(shipping_zone.countries.all()) for shipping_zone in warehouse_group_shipping_zones.all()], [])



        countries = []
        for index, cleaned_input in enumerate(cleaned_inputs):
            if not cleaned_input:
                continue

            for warehouse_group_country in warehouse_group_countries:
                if warehouse_group_country.code == cleaned_input['code'] and (any(province in cleaned_input['provinces'] for province in warehouse_group_country.provinces) or cleaned_input['provinces'] == warehouse_group_country.provinces):
                    raise ValidationError(
                        {
                            "countries": ValidationError(
                                "Some countries exists with another zone in the same group", code=ShippingErrorCode.DUPLICATED_COUNTRY_IN_GROUP.value
                            )
                        })

            country = shipping_zone.countries.filter(code=cleaned_input.get("code")).first()
            try:
                if country is not None:
                    instance = country
                else:
                    instance = models.ShippingCountry()

                cleaned_input["shipping_zone"] = shipping_zone
                instance = cls.construct_instance(instance, cleaned_input)
                cls.clean_instance(info, instance)
                countries.append(instance)
            except ValidationError as error:
                raise ValidationError(error)


        return countries
        

    @classmethod
    @transaction.atomic
    def save_countries(cls, info, instances, cleaned_inputs):
        assert len(instances) == len(
            cleaned_inputs
        ), "There should be the same number of instances and cleaned inputs."

        
        for instance, cleaned_input in zip(instances, cleaned_inputs):
            instance.save()

    @classmethod
    @transaction.atomic
    def save(cls, info, instance, cleaned_input):
        instance.save()

        countries_input = cleaned_input.get("countries", None)
        if countries_input is not None:
            countries = cls.update_or_create_countries(info, instance, countries_input)

        cls.save_countries(info, countries, countries_input)

        codes = list(map(lambda country: country.code, countries_input))

        for country in instance.countries.all():
            if country.code not in  codes:
                country.delete()



class ShippingZoneCreate(ShippingZoneMixin, ModelMutation):
    class Arguments:
        input = ShippingZoneInput(
            description="Fields required to create a shipping zone.", required=True
        )

    class Meta:
        description = "Creates a new shipping zone."
        model = models.ShippingZone
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"


class ShippingZoneUpdate(ShippingZoneMixin, ModelMutation):
    class Arguments:
        id = graphene.ID(description="ID of a shipping zone to update.", required=True)
        input = ShippingZoneInput(
            description="Fields required to update a shipping zone.", required=True
        )

    class Meta:
        description = "Updates a new shipping zone."
        model = models.ShippingZone
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"


class ShippingZoneDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a shipping zone to delete.")

    class Meta:
        description = "Deletes a shipping zone."
        model = models.ShippingZone
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"


class ShippingProfileMixin:
    @classmethod
    def clean_input(cls, info, instance, data, input_cls=None):
        duplicates_ids = get_duplicates_ids(
            data.get("add_products"), data.get("remove_products")
        )
        if duplicates_ids:
            error_msg = (
                "The same object cannot be in both lists "
                "for adding and removing items."
            )
            raise ValidationError(
                {
                    "removeProducts": ValidationError(
                        error_msg,
                        code=ShippingErrorCode.DUPLICATED_INPUT_ITEM.value,
                        params={"products": list(duplicates_ids)},
                    )
                }
            )

        cleaned_input = super().clean_input(info, instance, data)
        return cleaned_input
        
    @classmethod
    @transaction.atomic
    def save(cls, info, instance, cleaned_input):
        instance.save()

        add_products = cleaned_input.get("add_products")
        if add_products:
            for product in add_products:
                if product.shipping_profile != instance:
                    product.shipping_profile = instance
                    product.save()

        remove_products = cleaned_input.get("remove_products")
        if remove_products:
            for product in remove_products:
                if product.shipping_profile == instance:
                    product.shipping_profile = models.ShippingProfile.objects.filter(default=True).first()
                    product.save()


class ShippingProfileCreate(ShippingProfileMixin, ModelMutation):
    class Arguments:
        input = ShippingProfileCreateInput(
            description="Fields required to create a shipping profile.", required=True
        )

    class Meta:
        description = "Creates a new shipping profile."
        model = models.ShippingProfile
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"


class ShippingProfileUpdate(ShippingProfileMixin, ModelMutation):
    class Arguments:
        id = graphene.ID(description="ID of a shipping profile to update.", required=True)
        input = ShippingProfileUpdateInput(
            description="Fields required to update a shipping profile.", required=True
        )

    class Meta:
        description = "Updates a shipping profile."
        model = models.ShippingProfile
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"


class ShippingProfileDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a shipping profile to delete.")

    class Meta:
        description = "Deletes a shipping profile."
        model = models.ShippingProfile
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"
        
    @classmethod
    def perform_mutation(cls, root, info, **data):
        shipping_profile = cls.get_node_or_error(
            info, data.get("id"), only_type=ShippingProfile
        )

        if shipping_profile.default:
            error_msg = (
                "Cannot delete default shipping "
                "profile."
            )
            raise ValidationError(
                {
                    "id": ValidationError(
                        error_msg,
                        code=ShippingErrorCode.DEFAULT_SHIPPING_PROFILE.value,
                    )
                }
            )

        return super().perform_mutation(root, info, **data)


class ShippingProfileWarehouseGroupMixin:
    @classmethod
    def clean_input(cls, info, instance, data, input_cls=None):
        duplicates_ids = get_duplicates_ids(
            data.get("add_warehouses"), data.get("remove_warehouses")
        )
        if duplicates_ids:
            error_msg = (
                "The same object cannot be in both lists "
                "for adding and removing items."
            )
            raise ValidationError(
                {
                    "removeWarehouses": ValidationError(
                        error_msg,
                        code=ShippingErrorCode.DUPLICATED_INPUT_ITEM.value,
                        params={"warehouses": list(duplicates_ids)},
                    )
                }
            )

        cleaned_input = super().clean_input(info, instance, data)
        return cleaned_input
        
    @classmethod
    @transaction.atomic
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)

        add_warehouses = cleaned_data.get("add_warehouses")
        if add_warehouses:
            for warehouse_group in instance.shipping_profile.warehouse_groups.exclude(pk=instance.pk).all():
                warehouse_group.warehouses.remove(*add_warehouses)

                if not warehouse_group.warehouses.all().exists():
                    warehouse_group.delete()

            instance.warehouses.add(*add_warehouses)

        remove_warehouses = cleaned_data.get("remove_warehouses")
        if remove_warehouses:
            instance.warehouses.remove(*remove_warehouses)

            if not instance.warehouses.all().exists():
                instance.delete()



class ShippingProfileWarehouseGroupCreate(ShippingProfileWarehouseGroupMixin, ModelMutation):

    shipping_profile = graphene.Field(
        ShippingProfile,
        description="A shipping profile to which the shipping profile warehouse group.",
    )

    class Arguments:
        input = ShippingProfileWarehouseGroupCreateInput(
            description="Fields required to create a shipping profile warehouse group.", required=True
        )

    class Meta:
        description = "Creates a new shipping profile warehouse group."
        model = models.ShippingProfileWarehouseGroup
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"

    @classmethod
    def success_response(cls, instance):
        response = super().success_response(instance)
        response.shipping_profile = instance.shipping_profile
        return response



class ShippingProfileWarehouseGroupUpdate(ShippingProfileWarehouseGroupMixin, ModelMutation):

    shipping_profile = graphene.Field(
        ShippingProfile,
        description="A shipping profile to which the shipping profile warehouse group.",
    )

    class Arguments:
        id = graphene.ID(description="IDID of a shipping profile warehouse group to update.", required=True)
        input = ShippingProfileWarehouseGroupUpdateInput(
            description="Fields required to update a shipping profile warehouse group.", required=True
        )

    class Meta:
        description = "Updates a shipping profile."
        model = models.ShippingProfileWarehouseGroup
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"

    @classmethod
    @transaction.atomic
    def save(cls, info, instance, cleaned_input):
        instance.save()

    @classmethod
    def success_response(cls, instance):
        response = super().success_response(instance)
        response.shipping_profile = instance.shipping_profile
        return response


class ShippingMethodMixin:
    @classmethod
    def clean_input(cls, info, instance, data, input_cls=None):
        cleaned_input = super().clean_input(info, instance, data)

        # Rename the price field to price_amount (the model's)
        price_amount = cleaned_input.pop("price", None)
        if price_amount is not None:
            if price_amount < 0:
                raise ValidationError(
                    {
                        "price": ValidationError(
                            ("Shipping rate price cannot be lower than 0."),
                            code=ShippingErrorCode.INVALID,
                        )
                    }
                )
            cleaned_input["price_amount"] = price_amount

        cleaned_type = cleaned_input.get("type")
        if cleaned_type:
            if cleaned_type == ShippingMethodTypeEnum.PRICE.value:
                min_price = cleaned_input.pop("minimum_order_price", None)
                max_price = cleaned_input.pop("maximum_order_price", None)

                if min_price is not None:
                    cleaned_input["minimum_order_price_amount"] = min_price

                if max_price is not None:
                    cleaned_input["maximum_order_price_amount"] = max_price

                if (
                    min_price is not None
                    and max_price is not None
                    and max_price <= min_price
                ):
                    raise ValidationError(
                        {
                            "maximum_order_price": ValidationError(
                                (
                                    "Maximum order price should be larger than "
                                    "the minimum order price."
                                ),
                                code=ShippingErrorCode.MAX_LESS_THAN_MIN,
                            )
                        }
                    )
                cleaned_input["minimum_order_weight"] = None
                cleaned_input["maximum_order_weight"] = None

            elif cleaned_type == ShippingMethodTypeEnum.WEIGHT.value:
                min_weight = cleaned_input.get("minimum_order_weight")
                max_weight = cleaned_input.get("maximum_order_weight")

                if min_weight and min_weight.value < 0:
                    raise ValidationError(
                        {
                            "minimum_order_weight": ValidationError(
                                "Shipping can't have negative weight.",
                                code=ShippingErrorCode.INVALID,
                            )
                        }
                    )

                if max_weight and max_weight.value < 0:
                    raise ValidationError(
                        {
                            "maximum_order_weight": ValidationError(
                                "Shipping can't have negative weight.",
                                code=ShippingErrorCode.INVALID,
                            )
                        }
                    )

                if (
                    min_weight is not None
                    and max_weight is not None
                    and max_weight <= min_weight
                ):
                    raise ValidationError(
                        {
                            "maximum_order_weight": ValidationError(
                                (
                                    "Maximum order weight should be larger than the "
                                    "minimum order weight."
                                ),
                                code=ShippingErrorCode.MAX_LESS_THAN_MIN,
                            )
                        }
                    )

                cleaned_input["minimum_order_price"] = None
                cleaned_input["maximum_order_price"] = None

            elif cleaned_type == ShippingMethodTypeEnum.GENERAL.value:
                cleaned_input["minimum_order_price"] = None
                cleaned_input["maximum_order_price"] = None
                cleaned_input["minimum_order_weight"] = None
                cleaned_input["maximum_order_weight"] = None

        return cleaned_input


class ShippingMethodCreate(ShippingMethodMixin, ModelMutation):
    shipping_zone = graphene.Field(
        ShippingZone,
        description="A shipping zone to which the shipping method belongs.",
    )

    class Arguments:
        input = ShippingMethodInput(
            description="Fields required to create a shipping method.", required=True
        )

    class Meta:
        description = "Creates a new shipping method."
        model = models.ShippingMethod
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"

    @classmethod
    def success_response(cls, instance):
        response = super().success_response(instance)
        response.shipping_zone = instance.shipping_zone
        return response


class ShippingMethodUpdate(ShippingMethodMixin, ModelMutation):
    shipping_zone = graphene.Field(
        ShippingZone,
        description="A shipping zone to which the shipping method belongs.",
    )

    class Arguments:
        id = graphene.ID(description="ID of a shipping method to update.", required=True)
        input = ShippingMethodInput(
            description="Fields required to update a shipping method.", required=True
        )

    class Meta:
        description = "Updates a new shipping method."
        model = models.ShippingMethod
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"

    @classmethod
    def success_response(cls, instance):
        response = super().success_response(instance)
        response.shipping_zone = instance.shipping_zone
        return response


class ShippingMethodDelete(BaseMutation):
    shipping_method = graphene.Field(
        ShippingMethod, description="A shipping method to delete."
    )
    shipping_zone = graphene.Field(
        ShippingZone,
        description="A shipping zone to which the shipping method belongs.",
    )

    class Arguments:
        id = graphene.ID(required=True, description="ID of a shipping method to delete.")

    class Meta:
        description = "Deletes a shipping method."
        permissions = (ShippingPermissions.MANAGE_SHIPPING,)
        error_type_class = ShippingError
        error_type_field = "shipping_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        shipping_method = cls.get_node_or_error(
            info, data.get("id"), only_type=ShippingMethod
        )
        shipping_method_id = shipping_method.id
        shipping_zone = shipping_method.shipping_zone
        shipping_method.delete()
        shipping_method.id = shipping_method_id
        return ShippingMethodDelete(
            shipping_method=shipping_method, shipping_zone=shipping_zone
        )
