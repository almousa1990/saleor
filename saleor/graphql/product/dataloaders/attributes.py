from collections import defaultdict

from promise import Promise

from ....core.permissions import ProductPermissions
from ....product.models import (
    AssignedProductAttribute,
    AssignedVariantAttribute,
    Attribute,
    AttributeValue,
)
from ...core.dataloaders import DataLoader
from .products import ProductByIdLoader, ProductVariantByIdLoader


class AttributeValuesByAttributeIdLoader(DataLoader):
    context_key = "attributevalues_by_attribute"

    def batch_load(self, keys):
        attribute_values = AttributeValue.objects.filter(attribute_id__in=keys)
        attribute_to_attributevalues = defaultdict(list)
        for attribute_value in attribute_values.iterator():
            attribute_to_attributevalues[attribute_value.attribute_id].append(
                attribute_value
            )
        return [attribute_to_attributevalues[attribute_id] for attribute_id in keys]


class AttributesByAttributeId(DataLoader):
    context_key = "attributes_by_id"

    def batch_load(self, keys):
        attributes = Attribute.objects.in_bulk(keys)
        return [attributes.get(key) for key in keys]

class AttributeProductsByProductTypeIdLoader(DataLoader):
    context_key = "attributeproducts_by_producttype"

    def batch_load(self, keys):
        user = self.user
        if user.is_active and user.has_perm(ProductPermissions.MANAGE_PRODUCTS):
            qs = AttributeProduct.objects.all()
        else:
            qs = AttributeProduct.objects.filter(attribute__visible_in_storefront=True)
        attribute_products = qs.filter(product_type_id__in=keys)
        producttype_to_attributeproducts = defaultdict(list)
        for attribute_product in attribute_products:
            producttype_to_attributeproducts[attribute_product.product_type_id].append(
                attribute_product
            )
        return [producttype_to_attributeproducts[key] for key in keys]


class AttributeVariantsByProductTypeIdLoader(DataLoader):
    context_key = "attributevariants_by_producttype"

    def batch_load(self, keys):
        user = self.user
        if user.is_active and user.has_perm(ProductPermissions.MANAGE_PRODUCTS):
            qs = AttributeVariant.objects.all()
        else:
            qs = AttributeVariant.objects.filter(attribute__visible_in_storefront=True)
        attribute_variants = qs.filter(product_type_id__in=keys)
        producttype_to_attributevariants = defaultdict(list)
        for attribute_variant in attribute_variants:
            producttype_to_attributevariants[attribute_variant.product_type_id].append(
                attribute_variant
            )
        return [producttype_to_attributevariants[key] for key in keys]


class AssignedProductAttributesByProductIdLoader(DataLoader):
    context_key = "assignedproductattributes_by_product"

    def batch_load(self, keys):
        user = self.user
        if user.is_active and user.has_perm(ProductPermissions.MANAGE_PRODUCTS):
            qs = AssignedVariantAttribute.objects.filter()
        else:
            qs = AssignedVariantAttribute.objects.filter(
                attribute__visible_in_storefront=True
            )
        assigned_product_attributes = qs.filter(variant__product_id__in=keys)
        product_to_assignedproductattributes = defaultdict(list)
        for assigned_product_attribute in assigned_product_attributes:
            product_to_assignedproductattributes[
                assigned_product_attribute.variant.product_id
            ].append(assigned_product_attribute)
        return [product_to_assignedproductattributes[product_id] for product_id in keys]


class AssignedVariantAttributesByProductVariantId(DataLoader):
    context_key = "assignedvariantattributes_by_productvariant"

    def batch_load(self, keys):
        user = self.user
        if user.is_active and user.has_perm(ProductPermissions.MANAGE_PRODUCTS):
            qs = AssignedVariantAttribute.objects.all()
        else:
            qs = AssignedVariantAttribute.objects.filter(
                attribute__visible_in_storefront=True
            )
        assigned_variant_attributes = qs.filter(variant_id__in=keys).select_related(
            "attribute"
        )
        variant_attributes = defaultdict(list)
        for assigned_variant_attribute in assigned_variant_attributes:
            variant_attributes[assigned_variant_attribute.variant_id].append(
                assigned_variant_attribute
            )
        return [variant_attributes[variant_id] for variant_id in keys]


class AttributeValueByIdLoader(DataLoader):
    context_key = "attributevalue_by_id"

    def batch_load(self, keys):
        attribute_values = AttributeValue.objects.in_bulk(keys)
        return [attribute_values.get(attribute_value_id) for attribute_value_id in keys]


class AttributeValuesByAssignedProductAttributeIdLoader(DataLoader):
    context_key = "attributevalues_by_assignedproductattribute"

    def batch_load(self, keys):
        AttributeAssignment = AttributeValue.assignedproductattribute_set.through
        attribute_values = AttributeAssignment.objects.filter(
            assignedproductattribute_id__in=keys
        )
        value_ids = [a.attributevalue_id for a in attribute_values]

        def map_assignment_to_values(values):
            value_map = dict(zip(value_ids, values))
            assigned_product_map = defaultdict(list)
            for attribute_value in attribute_values:
                assigned_product_map[
                    attribute_value.assignedproductattribute_id
                ].append(value_map.get(attribute_value.attributevalue_id))
            return [
                sorted(assigned_product_map[key], key=lambda v: (v.sort_order, v.id))
                for key in keys
            ]

        return (
            AttributeValueByIdLoader(self.context)
            .load_many(value_ids)
            .then(map_assignment_to_values)
        )


class AttributeValuesByAssignedVariantAttributeIdLoader(DataLoader):
    context_key = "attributevalues_by_assignedvariantattribute"

    def batch_load(self, keys):
        AttributeAssignment = AttributeValue.assignedvariantattribute_set.through
        attribute_values = AttributeAssignment.objects.filter(
            assignedvariantattribute_id__in=keys
        )
        value_ids = [a.attributevalue_id for a in attribute_values]

        def map_assignment_to_values(values):
            value_map = dict(zip(value_ids, values))
            assigned_variant_map = defaultdict(list)
            for attribute_value in attribute_values:
                assigned_variant_map[
                    attribute_value.assignedvariantattribute_id
                ].append(value_map.get(attribute_value.attributevalue_id))
            return [
                sorted(assigned_variant_map[key], key=lambda v: (v.sort_order, v.id))
                for key in keys
            ]

        return (
            AttributeValueByIdLoader(self.context)
            .load_many(value_ids)
            .then(map_assignment_to_values)
        )


class SelectedAttributesByProductIdLoader(DataLoader):
    context_key = "selectedattributes_by_product"

    def batch_load(self, keys):
        def with_products_and_assigned_attributed(result):
            product_attributes = result
            assigned_product_attribute_ids = [
                a.id for attrs in product_attributes for a in attrs
            ]
            attribute_ids = [
                a.attribute_id for attrs in product_attributes for a in attrs
            ]
            product_attributes = dict(zip(keys, product_attributes))

            def with_attribute_values(result):
                attribute_values = dict(
                    zip(assigned_product_attribute_ids, result)
                )

                def with_attributes(attributes):
                    id_to_attribute = dict(zip(attribute_ids, attributes))
                    selected_attributes_map = defaultdict(list)
                    for key in keys:
                        assigned_product_attributes = product_attributes[key]
                        for (
                            assigned_product_attribute
                        ) in assigned_product_attributes:

                            attribute = id_to_attribute[
                                assigned_product_attribute.attribute_id
                            ]

                            values = attribute_values[assigned_product_attribute.id]
                            
                            existing_attribute = next((selected_attribute for selected_attribute in selected_attributes_map[key] if selected_attribute["attribute"].pk == attribute.pk), None)
                            if existing_attribute is None:
                                selected_attributes_map[key].append(
                                    {"values": values, "attribute": attribute}
                                )
                            else:
                                existing_value = next((selected_attribute_value for selected_attribute_value in existing_attribute["values"] if any(selected_attribute_value.pk == new_value.pk for new_value in values)), None)
                                if existing_value is None:
                                    new_values = values+existing_attribute["values"]
                                    existing_attribute.update({"values": new_values})

                    return [selected_attributes_map[key] for key in keys]

                return (
                    AttributesByAttributeId(self.context)
                    .load_many(attribute_ids)
                    .then(with_attributes)
                )
            if assigned_product_attribute_ids:
                attribute_values = AttributeValuesByAssignedVariantAttributeIdLoader(
                    self.context
                ).load_many(assigned_product_attribute_ids)

                return Promise.all(attribute_values).then(
                    with_attribute_values
                )
            else:
                return with_attribute_values([])


        assigned_attributes = AssignedProductAttributesByProductIdLoader(
            self.context
        ).load_many(keys)

        return Promise.all(assigned_attributes).then(
            with_products_and_assigned_attributed
        )

class SelectedAttributesByProductVariantIdLoader(DataLoader):
    context_key = "selectedattributes_by_productvariant"

    def batch_load(self, keys):
        def with_variants_and_assigned_attributed(results):
            variant_attributes = results
            attribute_ids = [
                a.attribute_id for attrs in variant_attributes for a in attrs
            ]
            assigned_variant_attribute_ids = [
                a.id for attrs in variant_attributes for a in attrs
            ]

            variant_attributes = dict(zip(keys, variant_attributes))

            def with_attribute_values(results):
                attribute_values = dict(
                    zip(assigned_variant_attribute_ids, results)
                )
                def with_attributes(attributes):
                    id_to_attribute = dict(zip(attribute_ids, attributes))
                    selected_attributes_map = defaultdict(list)
                    for key in keys:

                        assigned_variant_attributes = variant_attributes[key]
                        for (
                            assigned_variant_attribute
                        ) in assigned_variant_attributes:

                            attribute = id_to_attribute[
                                assigned_variant_attribute.attribute_id
                            ]
                            
                            values = attribute_values[assigned_variant_attribute.id]

                            selected_attributes_map[key].append(
                                {"values": values, "attribute": attribute}
                            )
                    return [selected_attributes_map[key] for key in keys]

                return (
                    AttributesByAttributeId(self.context)
                    .load_many(attribute_ids)
                    .then(with_attributes)
                )

            
            if assigned_variant_attribute_ids:
                attribute_values = AttributeValuesByAssignedVariantAttributeIdLoader(
                    self.context
                ).load_many(assigned_variant_attribute_ids)

                return Promise.all(attribute_values).then(
                    with_attribute_values
                )
            else:
                return with_attribute_values([])

        assigned_attributes = AssignedVariantAttributesByProductVariantId(
            self.context
        ).load_many(keys)

        return Promise.all(assigned_attributes).then(
            with_variants_and_assigned_attributed
        )

