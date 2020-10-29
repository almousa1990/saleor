from collections import defaultdict
from typing import Iterable, List, Tuple, Union

import graphene
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils.text import slugify
from graphene.types import InputObjectType
from graphql_relay import from_global_id

from ....core.exceptions import PermissionDenied
from ....core.permissions import ProductPermissions
from ....product import models
from ....product.error_codes import ProductErrorCode
from ....product.tasks import (
    update_product_minimal_variant_price_task,
    update_products_minimal_variant_prices_of_catalogues_task,
    update_variants_names,
)
from ....product.thumbnails import (
    create_category_background_image_thumbnails,
    create_collection_background_image_thumbnails,
    create_product_thumbnails,
)
from ....product.utils import delete_categories, delete_variants
from ....product.utils.attributes import (
    associate_attribute_values_to_instance,
    generate_name_for_variant,
)
from ...core.mutations import BaseMutation, ModelDeleteMutation, ModelMutation
from ...core.scalars import Decimal, WeightScalar
from ...core.types import SeoInput, Upload
from ...core.types.common import ProductError
from ...core.utils import (
    clean_seo_fields,
    from_global_id_strict_type,
    get_duplicated_values,
    validate_image_file,
    validate_slug_and_generate_if_needed,
    generate_unique_slug
)
from ...core.utils.reordering import perform_reordering
from ...meta.deprecated.mutations import ClearMetaBaseMutation, UpdateMetaBaseMutation
from ...warehouse.types import Warehouse
from ..types import Category, Collection, Product, ProductImage, ProductVariant
from ..utils import (
    create_stocks,
    get_used_attribute_values_for_variant,
    get_used_variants_attribute_values,
    validate_attribute_input_for_product,
    validate_attribute_input_for_variant,
)

from ....warehouse import models as warehouse_models

from django.core.files.base import ContentFile
from urllib import request
from django.core.files import File

class CategoryInput(graphene.InputObjectType):
    description = graphene.String(description="Category description (HTML/text).")
    description_json = graphene.JSONString(description="Category description (JSON).")
    name = graphene.String(description="Category name.")
    slug = graphene.String(description="Category slug.")
    seo = SeoInput(description="Search engine optimization fields.")
    background_image = Upload(description="Background image file.")
    background_image_alt = graphene.String(description="Alt text for an image.")


class CategoryCreate(ModelMutation):
    class Arguments:
        input = CategoryInput(
            required=True, description="Fields required to create a category."
        )
        parent_id = graphene.ID(
            description=(
                "ID of the parent category. If empty, category will be top level "
                "category."
            ),
            name="parent",
        )

    class Meta:
        description = "Creates a new category."
        model = models.Category
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = ProductErrorCode.REQUIRED.value
            raise ValidationError({"slug": error})
        parent_id = data["parent_id"]
        if parent_id:
            parent = cls.get_node_or_error(
                info, parent_id, field="parent", only_type=Category
            )
            cleaned_input["parent"] = parent
        if data.get("background_image"):
            image_data = info.context.FILES.get(data["background_image"])
            validate_image_file(image_data, "background_image")
        clean_seo_fields(cleaned_input)
        return cleaned_input

    @classmethod
    def perform_mutation(cls, root, info, **data):
        parent_id = data.pop("parent_id", None)
        data["input"]["parent_id"] = parent_id
        return super().perform_mutation(root, info, **data)

    @classmethod
    def save(cls, info, instance, cleaned_input):
        instance.save()
        if cleaned_input.get("background_image"):
            create_category_background_image_thumbnails.delay(instance.pk)


class CategoryUpdate(CategoryCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a category to update.")
        input = CategoryInput(
            required=True, description="Fields required to update a category."
        )

    class Meta:
        description = "Updates a category."
        model = models.Category
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"


class CategoryDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a category to delete.")

    class Meta:
        description = "Deletes a category."
        model = models.Category
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        if not cls.check_permissions(info.context):
            raise PermissionDenied()
        node_id = data.get("id")
        instance = cls.get_node_or_error(info, node_id, only_type=Category)

        db_id = instance.id

        delete_categories([db_id])

        instance.id = db_id
        return cls.success_response(instance)

class CategoryUpdateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.Category
        description = "Update public metadata for category."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class CategoryClearMeta(ClearMetaBaseMutation):
    class Meta:
        model = models.Category
        description = "Clears public metadata for category."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class CategoryUpdatePrivateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.Category
        description = "Update private metadata for category."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class CategoryClearPrivateMeta(ClearMetaBaseMutation):
    class Meta:
        model = models.Category
        description = "Clears private metadata for category."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"

class CollectionInput(graphene.InputObjectType):
    is_published = graphene.Boolean(
        description="Informs whether a collection is published."
    )
    name = graphene.String(description="Name of the collection.")
    slug = graphene.String(description="Slug of the collection.")
    description = graphene.String(
        description="Description of the collection (HTML/text)."
    )
    description_json = graphene.JSONString(
        description="Description of the collection (JSON)."
    )
    description_html = graphene.String(
        description="Description of the collection (HTML/text)."
    )
    background_image = Upload(description="Background image file.")
    background_image_alt = graphene.String(description="Alt text for an image.")
    seo = SeoInput(description="Search engine optimization fields.")
    publication_date = graphene.Date(description="Publication date. ISO 8601 standard.")


class CollectionCreateInput(CollectionInput):
    products = graphene.List(
        graphene.ID,
        description="List of products to be added to the collection.",
        name="products",
    )


class CollectionCreate(ModelMutation):
    class Arguments:
        input = CollectionCreateInput(
            required=True, description="Fields required to create a collection."
        )

    class Meta:
        description = "Creates a new collection."
        model = models.Collection
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = ProductErrorCode.REQUIRED.value
            raise ValidationError({"slug": error})
        if data.get("background_image"):
            image_data = info.context.FILES.get(data["background_image"])
            validate_image_file(image_data, "background_image")
        clean_seo_fields(cleaned_input)
        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        products = cleaned_data.get("products", None)
        if products is not None:
            for index, product in enumerate(products):
                collection_product = models.CollectionProduct(product=product, collection=instance, sort_order=index)
                collection_product.save()


    @classmethod
    def save(cls, info, instance, cleaned_input):
        instance.save()
        if cleaned_input.get("background_image"):
            create_collection_background_image_thumbnails.delay(instance.pk)


class CollectionUpdate(CollectionCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a collection to update.")
        input = CollectionInput(
            required=True, description="Fields required to update a collection."
        )

    class Meta:
        description = "Updates a collection."
        model = models.Collection
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def save(cls, info, instance, cleaned_input):
        if cleaned_input.get("background_image"):
            create_collection_background_image_thumbnails.delay(instance.pk)
        instance.save()


class CollectionDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a collection to delete.")

    class Meta:
        description = "Deletes a collection."
        model = models.Collection
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"


class MoveProductInput(graphene.InputObjectType):
    product_id = graphene.ID(
        description="The ID of the product to move.", required=True
    )
    sort_order = graphene.Int(
        description=(
            "The relative sorting position of the product (from -inf to +inf) "
            "starting from the first given product's actual position."
            "1 moves the item one position forward, -1 moves the item one position "
            "backward, 0 leaves the item unchanged."
        )
    )


class CollectionReorderProducts(BaseMutation):
    collection = graphene.Field(
        Collection, description="Collection from which products are reordered."
    )

    class Meta:
        description = "Reorder the products of a collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    class Arguments:
        collection_id = graphene.Argument(
            graphene.ID, required=True, description="ID of a collection."
        )
        moves = graphene.List(
            MoveProductInput,
            required=True,
            description="The collection products position operations.",
        )

    @classmethod
    def perform_mutation(cls, _root, info, collection_id, moves):
        pk = from_global_id_strict_type(
            collection_id, only_type=Collection, field="collection_id"
        )

        try:
            collection = models.Collection.objects.prefetch_related(
                "collectionproduct"
            ).get(pk=pk)
        except ObjectDoesNotExist:
            raise ValidationError(
                {
                    "collection_id": ValidationError(
                        f"Couldn't resolve to a collection: {collection_id}",
                        code=ProductErrorCode.NOT_FOUND,
                    )
                }
            )

        m2m_related_field = collection.collectionproduct

        operations = {}

        # Resolve the products
        for move_info in moves:
            product_pk = from_global_id_strict_type(
                move_info.product_id, only_type=Product, field="moves"
            )

            try:
                m2m_info = m2m_related_field.get(product_id=int(product_pk))
            except ObjectDoesNotExist:
                raise ValidationError(
                    {
                        "moves": ValidationError(
                            f"Couldn't resolve to a product: {move_info.product_id}",
                            code=ProductErrorCode.NOT_FOUND,
                        )
                    }
                )
            operations[m2m_info.pk] = move_info.sort_order

        with transaction.atomic():
            perform_reordering(m2m_related_field, operations)
        return CollectionReorderProducts(collection=collection)


class CollectionAddProducts(BaseMutation):
    collection = graphene.Field(
        Collection, description="Collection to which products will be added."
    )

    class Arguments:
        collection_id = graphene.Argument(
            graphene.ID, required=True, description="ID of a collection."
        )
        products = graphene.List(
            graphene.ID, required=True, description="List of product IDs."
        )

    class Meta:
        description = "Adds products to a collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    @transaction.atomic()
    def perform_mutation(cls, _root, info, collection_id, products):
        collection = cls.get_node_or_error(
            info, collection_id, field="collection_id", only_type=Collection
        )
        products = cls.get_nodes_or_error(products, "products", Product)

        for product in products:
            collection_product = models.CollectionProduct(product=product, collection=collection)
            collection_product.save()

        #collection.products.add(*products)
        if collection.sale_set.exists():
            # Updated the db entries, recalculating discounts of affected products
            update_products_minimal_variant_prices_of_catalogues_task.delay(
                product_ids=[p.pk for p in products]
            )
        return CollectionAddProducts(collection=collection)


class CollectionRemoveProducts(BaseMutation):
    collection = graphene.Field(
        Collection, description="Collection from which products will be removed."
    )

    class Arguments:
        collection_id = graphene.Argument(
            graphene.ID, required=True, description="ID of a collection."
        )
        products = graphene.List(
            graphene.ID, required=True, description="List of product IDs."
        )

    class Meta:
        description = "Remove products from a collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, collection_id, products):
        collection = cls.get_node_or_error(
            info, collection_id, field="collection_id", only_type=Collection
        )
        products = cls.get_nodes_or_error(products, "products", only_type=Product)

        for collection_product in models.CollectionProduct.objects.filter(product_id__in = [product.pk for product in products]):
            collection_product.delete()

        #collection.products.remove(*products)
        if collection.sale_set.exists():
            # Updated the db entries, recalculating discounts of affected products
            update_products_minimal_variant_prices_of_catalogues_task.delay(
                product_ids=[p.pk for p in products]
            )
        return CollectionRemoveProducts(collection=collection)


class CollectionUpdateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.Collection
        description = "Update public metadata for collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class CollectionClearMeta(ClearMetaBaseMutation):
    class Meta:
        model = models.Collection
        description = "Clears public metadata for collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class CollectionUpdatePrivateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.Collection
        description = "Update private metadata for collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class CollectionClearPrivateMeta(ClearMetaBaseMutation):
    class Meta:
        model = models.Collection
        description = "Clears private metadata item for collection."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class AttributeValueInput(InputObjectType):
    id = graphene.ID(description="ID of the selected attribute.")
    values = graphene.List(
        graphene.String,
        required=True,
        description=(
            "The value or slug of an attribute to resolve. "
            "If the passed value is non-existent, it will be created."
        ),
    )


class StockInput(graphene.InputObjectType):
    warehouse = graphene.ID(
        required=True, description="Warehouse in which stock is located."
    )
    quantity = graphene.Int(description="Quantity of items available for sell.")


class ProductVariantInput(graphene.InputObjectType):

    id = graphene.ID(
        required=False, description="ID of a product variant to update."
    )

    attributes = graphene.List(
        AttributeValueInput,
        required=False,
        description="List of attributes specific to this variant.",
    )

    charge_taxes = graphene.Boolean(
        description="Determine if taxes are being charged for the product."
    )

    tax_code = graphene.String(description="Tax rate for enabled tax gateway.")
    compare_at_price = Decimal(description="The compare-at price of the variant.")
    cost_price = Decimal(description="Cost price of the variant.")
    price = Decimal(description="Price of the particular variant.")
    sku = graphene.String(description="Stock keeping unit.")
    barcode = graphene.String(
        description="The value of the barcode associated with the product.")
    requires_shipping = graphene.Boolean(
        description="Whether the variant requires shipping."
    )
    track_inventory = graphene.Boolean(
        description=(
            "Determines if the inventory of this variant should be tracked. If false, "
            "the quantity won't change when customers buy this item."
        )
    )
    weight = WeightScalar(description="Weight of the Product Variant.", required=False)

    product = graphene.ID(
        description="Product ID of which type is the variant.",
        name="product",
        required=False,
    )
    stocks = graphene.List(
        graphene.NonNull(StockInput),
        description=("Stocks of a product available for sale."),
        required=False,
    )



class ImageInput(graphene.InputObjectType):
    alt = graphene.String(description="Alt text for an image.")
    url = graphene.String(
        description="The URL of the image. May be a staged upload URL.")

        
class ProductInput(graphene.InputObjectType):
    id = graphene.ID(
        required=False, description="ID of a product variant to update."
    )
    attributes = graphene.List(AttributeValueInput, description="List of attributes.")

    product_type = graphene.ID(
        description="ID of the type that product belongs to.",
        name="productType"
    )

    vendor = graphene.ID(
        description="ID of the Vendor.",
        name="vendor"
    )

    publication_date = graphene.types.datetime.Date(
        description="Publication date. ISO 8601 standard."
    )
    collections = graphene.List(
        graphene.ID,
        description="List of IDs of collections that the product belongs to.",
        name="collections",
    )
    description_html = graphene.String(description="Product description (HTML/text).")
    is_published = graphene.Boolean(
        description="Determines if product is visible to customers."
    )
    name = graphene.String(description="Product name.")
    slug = graphene.String(description="Product slug.")
    seo = SeoInput(description="Search engine optimization fields.")

    tags = graphene.List(
        graphene.NonNull(graphene.String),
        required=False,
        description="List of tags that have been added to the product",
    )
    variants = graphene.List(graphene.NonNull(ProductVariantInput),
                             description="A list of variants associated with the product.")

        
    images = graphene.List(graphene.NonNull(ImageInput),
                        description="The images to associate with the product")





T_INPUT_MAP = List[Tuple[models.Attribute, List[str]]]
T_INSTANCE = Union[models.Product, models.ProductVariant]


class AttributeAssignmentMixin:
    """Handles cleaning of the attribute input and creating the proper relations.

    1. You should first call ``clean_input``, to transform and attempt to resolve
       the provided input into actual objects. It will then perform a few
       checks to validate the operations supplied by the user are possible and allowed.
    2. Once everything is ready and all your data is saved inside a transaction,
       you shall call ``save`` with the cleaned input to build all the required
       relations. Once the ``save`` call is done, you are safe from continuing working
       or to commit the transaction.

    Note: you shall never call ``save`` outside of a transaction and never before
    the targeted instance owns a primary key. Failing to do so, the relations will
    be unable to build or might only be partially built.
    """

    @classmethod
    def _resolve_attribute_nodes(
        cls,
        qs: QuerySet,
        *,
        global_ids: List[str],
        pks: Iterable[int],
        slugs: Iterable[str],
    ):
        """Retrieve attributes nodes from given global IDs and/or slugs."""
        qs = qs.filter(Q(pk__in=pks) | Q(slug__in=slugs))
        nodes = list(qs)  # type: List[models.Attribute]

        if not nodes:
            raise ValidationError(
                (
                    f"Could not resolve to a node: ids={global_ids}"
                    f" and slugs={list(slugs)}"
                ),
                code=ProductErrorCode.NOT_FOUND.value,
            )

        nodes_pk_list = set()
        nodes_slug_list = set()
        for node in nodes:
            nodes_pk_list.add(node.pk)
            nodes_slug_list.add(node.slug)

        for pk, global_id in zip(pks, global_ids):
            if pk not in nodes_pk_list:
                raise ValidationError(
                    f"Could not resolve {global_id!r} to Attribute",
                    code=ProductErrorCode.NOT_FOUND.value,
                )

        for slug in slugs:
            if slug not in nodes_slug_list:
                raise ValidationError(
                    f"Could not resolve slug {slug!r} to Attribute",
                    code=ProductErrorCode.NOT_FOUND.value,
                )

        return nodes

    @classmethod
    def _resolve_attribute_global_id(cls, global_id: str) -> int:
        """Resolve an Attribute global ID into an internal ID (int)."""
        graphene_type, internal_id = from_global_id(global_id)  # type: str, str
        if graphene_type != "Attribute":
            raise ValidationError(
                f"Must receive an Attribute id, got {graphene_type}.",
                code=ProductErrorCode.INVALID.value,
            )
        if not internal_id.isnumeric():
            raise ValidationError(
                f"An invalid ID value was passed: {global_id}",
                code=ProductErrorCode.INVALID.value,
            )
        return int(internal_id)

    @classmethod
    def _pre_save_values(cls, attribute: models.Attribute, values: List[str]):
        """Lazy-retrieve or create the database objects from the supplied raw values."""
        get_or_create = attribute.values.get_or_create
        return tuple(
            get_or_create(
                attribute=attribute,
                slug=slugify(value, allow_unicode=True),
                defaults={"name": value},
            )[0]
            for value in values
        )

    @classmethod
    def _check_input_for_product(cls, cleaned_input: T_INPUT_MAP, qs: QuerySet):
        """Check the cleaned attribute input for a product.

        An Attribute queryset is supplied.

        - ensure all required attributes are passed
        - ensure the values are correct for a product
        """
        supplied_attribute_pk = []
        for attribute, values in cleaned_input:
            validate_attribute_input_for_product(attribute, values)
            supplied_attribute_pk.append(attribute.pk)

        # Asserts all required attributes are supplied
        missing_required_filter = Q(value_required=True) & ~Q(
            pk__in=supplied_attribute_pk
        )

        if qs.filter(missing_required_filter).exists():
            raise ValidationError(
                "All attributes flagged as having a value required must be supplied.",
                code=ProductErrorCode.REQUIRED.value,
            )

    @classmethod
    def _check_input_for_variant(cls, cleaned_input: T_INPUT_MAP, qs: QuerySet):
        """Check the cleaned attribute input for a variant.

        An Attribute queryset is supplied.

        - ensure all attributes are passed
        - ensure the values are correct for a variant
        """
        #if len(cleaned_input) != qs.count():
        #    raise ValidationError(
        #        "All attributes must take a value", code=ProductErrorCode.REQUIRED.value
        #    )

        for attribute, values in cleaned_input:
            validate_attribute_input_for_variant(attribute, values)

    @classmethod
    def _validate_input(
        cls, cleaned_input: T_INPUT_MAP, attribute_qs, is_variant: bool
    ):
        """Check if no invalid operations were supplied.

        :raises ValidationError: when an invalid operation was found.
        """
        if is_variant:
            return cls._check_input_for_variant(cleaned_input, attribute_qs)
        else:
            return cls._check_input_for_product(cleaned_input, attribute_qs)

    @classmethod
    def clean_input(
        cls, raw_input: dict, attributes_qs: QuerySet, is_variant: bool
    ) -> T_INPUT_MAP:
        """Resolve and prepare the input for further checks.

        :param raw_input: The user's attributes input.
        :param attributes_qs:
            A queryset of attributes, the attribute values must be prefetched.
            Prefetch is needed by ``_pre_save_values`` during save.
        :param is_variant: Whether the input is for a variant or a product.

        :raises ValidationError: contain the message.
        :return: The resolved data
        """

        # Mapping to associate the input values back to the resolved attribute nodes
        pks = {}
        slugs = {}

        # Temporary storage of the passed ID for error reporting
        global_ids = []

        for attribute_input in raw_input:
            global_id = attribute_input.get("id")
            slug = attribute_input.get("slug")
            values = attribute_input["values"]

            if global_id:
                internal_id = cls._resolve_attribute_global_id(global_id)
                global_ids.append(global_id)
                pks[internal_id] = values
            elif slug:
                slugs[slug] = values
            else:
                raise ValidationError(
                    "You must whether supply an ID or a slug",
                    code=ProductErrorCode.REQUIRED.value,
                )

        attributes = cls._resolve_attribute_nodes(
            attributes_qs, global_ids=global_ids, pks=pks.keys(), slugs=slugs.keys()
        )
        cleaned_input = []
        for attribute in attributes:
            key = pks.get(attribute.pk, None)

            # Retrieve the primary key by slug if it
            # was not resolved through a global ID but a slug
            if key is None:
                key = slugs[attribute.slug]

            cleaned_input.append((attribute, key))
        cls._validate_input(cleaned_input, attributes_qs, is_variant)
        return cleaned_input

    @classmethod
    def save(cls, instance: T_INSTANCE, cleaned_input: T_INPUT_MAP):
        """Save the cleaned input into the database against the given instance.

        Note: this should always be ran inside a transaction.

        :param instance: the product or variant to associate the attribute against.
        :param cleaned_input: the cleaned user input (refer to clean_attributes)
        """
        for attribute, values in cleaned_input:
            attribute_values = cls._pre_save_values(attribute, values)
            associate_attribute_values_to_instance(
                instance, attribute, *attribute_values
            )


class ProductCreate(ModelMutation):
    class Arguments:
        input = ProductInput(
            required=True, description="Fields required to create a product."
            
        )

    class Meta:
        description = "Creates a new product."
        model = models.Product
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"
        
    @classmethod
    def clean_attributes(
        cls, attributes: dict
    ) -> T_INPUT_MAP:
        attributes = AttributeAssignmentMixin.clean_input(
            attributes, models.Attribute.objects.all(), is_variant=False
        )
        return attributes

    @classmethod
    def clean_image_input(
        cls,
        info,
        instance: models.ProductImage,
        data: dict,
        errors: dict,
        image_index: int,
    ):
        #cleaned_input = ModelMutation.clean_input(
        #    info, instance, data, input_cls=ProductImageCreateInput
        #)
        cleaned_input = data
        return cleaned_input

    @classmethod
    def clean_images(cls, info, images):
        cleaned_inputs = []
        errors = defaultdict(list)
        for index, image_data in enumerate(images):
            cleaned_input = None
            cleaned_input = cls.clean_image_input(
                info, None, image_data, errors, index
            )

            cleaned_inputs.append(cleaned_input if cleaned_input else None)

        if errors:
            raise ValidationError(errors)
        return cleaned_inputs

    @classmethod
    def clean_stocks(cls, stocks_data, errors, variant_index):
        warehouse_ids = [stock["warehouse"] for stock in stocks_data]
        quantities = [stock["quantity"] for stock in stocks_data]

        duplicates = get_duplicated_values(warehouse_ids)
        if duplicates:
            errors["stocks"] = ValidationError(
                "Duplicated warehouse ID.",
                code=ProductErrorCode.DUPLICATED_INPUT_ITEM,
                params={"warehouses": duplicates, "index": variant_index},
            )
        if sum(n < 0 for n in quantities):
            errors["stocks"] = ValidationError(
                "Negative stock value.",
                code=ProductErrorCode.INVALID,
                params={"warehouses": duplicates, "index": variant_index},
            )    

    @classmethod
    def clean_variant_input(
        cls,
        info,
        instance: models.ProductVariant,
        data: dict,
        errors: dict,
        variant_index: int,
    ):
        cleaned_input = ModelMutation.clean_input(
            info, instance, data, input_cls=ProductVariantInput
        )

        cost_price_amount = cleaned_input.pop("cost_price", None)
        if cost_price_amount is not None:
            if cost_price_amount < 0:
                errors["costPrice"] = ValidationError(
                    "Product price cannot be lower than 0.",
                    code=ProductErrorCode.INVALID.value,
                    params={"index": variant_index},
                )
            cleaned_input["cost_price_amount"] = cost_price_amount

        compare_at_price_amount = cleaned_input.pop("compare_at_price", None)
        if compare_at_price_amount is not None:
            if compare_at_price_amount < 0:
                errors["compareAtPrice"] = ValidationError(
                    "Product compare at price cannot be lower than 0.",
                    code=ProductErrorCode.INVALID.value,
                    params={"index": variant_index},
                )
            cleaned_input["compare_at_price_amount"] = compare_at_price_amount

        price_amount = cleaned_input.pop("price", None)
        if price_amount is not None:
            if price_amount < 0:
                errors["price"] = ValidationError(
                    "Product price cannot be lower than 0.",
                    code=ProductErrorCode.INVALID.value,
                    params={"index": variant_index},
                )
            cleaned_input["price_amount"] = price_amount

        attributes = cleaned_input.get("attributes")
        if attributes:
            try:
                cleaned_input["attributes"] = ProductVariantCreate.clean_attributes(
                    attributes
                )
            except ValidationError as exc:
                exc.params = {"index": variant_index}
                errors["attributes"] = exc
                
        stocks = cleaned_input.get("stocks")
        if stocks:
            cls.clean_stocks(stocks, errors, variant_index)

        return cleaned_input

    @classmethod
    def validate_duplicated_sku(cls, sku, index, sku_list, errors):
        if sku in sku_list:
            errors["sku"].append(
                ValidationError(
                    "Duplicated SKU.", ProductErrorCode.UNIQUE, params={"index": index}
                )
            )
        sku_list.append(sku)

    @classmethod
    def clean_variants(cls, info, variants, product, errors):
        cleaned_inputs = []
        sku_list = []
        used_attribute_values = get_used_variants_attribute_values(product)
        for index, variant_data in enumerate(variants):
            try:
                if variant_data.attributes is None:
                    variant_data.attributes = []

                if variant_data.id is not None:
                    instance = cls.get_node_or_error(info, variant_data.id, models.ProductVariant)
                    ProductVariantUpdate.validate_duplicated_attribute_values(
                        variant_data.attributes, used_attribute_values, instance
                    )
                else:
                    ProductVariantCreate.validate_duplicated_attribute_values(
                        variant_data.attributes, used_attribute_values
                    )
            except ValidationError as exc:
                errors["attributes"].append(
                    ValidationError(exc.message, exc.code, params={"index": index})
                )

            cleaned_input = None
            cleaned_input = cls.clean_variant_input(
                info, None, variant_data, errors, index
            )

            cleaned_inputs.append(cleaned_input if cleaned_input else None)

            if not variant_data.sku:
                continue
            cls.validate_duplicated_sku(variant_data.sku, index, sku_list, errors)
        return cleaned_inputs

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        errors = defaultdict(list)

        if cleaned_input.get("product_type") is not None:
            product_type = (
                instance.product_type if instance.pk else cleaned_input.get("product_type")
            )
            
        if cleaned_input.get("slug") is not None or instance._state.adding:
            try:
                cleaned_input = validate_slug_and_generate_if_needed(
                    instance, "name", cleaned_input
                )
            except ValidationError as error:
                error.code = ProductErrorCode.REQUIRED.value
                raise ValidationError({"slug": error})

        is_published = cleaned_input.get("is_published")

        clean_seo_fields(cleaned_input)

        variants = cleaned_input.pop("variants", None)
        if variants:
            cleaned_input["variants"] = cls.clean_variants(info, variants,instance, errors)

        images = cleaned_input.pop("images", None)
        if images:
            cleaned_input["images"] = cls.clean_images(info, images)

        if errors:
            raise ValidationError(errors)
        return cleaned_input

    @classmethod
    def get_instance(cls, info, **data):
        """Prefetch related fields that are needed to process the mutation."""
        # If we are updating an instance and want to update its attributes,
        # prefetch them.

        object_id = data.get("id")

        return super().get_instance(info, **data)

    @classmethod
    def get_remote_image(self, url):
        if url:
            result = request.urlretrieve(url)
            return File(open(result[0], 'rb'))
    

    @classmethod
    def add_indexes_to_errors(cls, index, error, error_dict):
        """Append errors with index in params to mutation error dict."""
        for key, value in error.error_dict.items():
            for e in value:
                if e.params:
                    e.params["index"] = index
                else:
                    e.params = {"index": index}
            error_dict[key].extend(value)

    @classmethod
    def create_images(cls, info, cleaned_inputs, product, errors):
        instances = []
        for index, cleaned_input in enumerate(cleaned_inputs):
            if not cleaned_input:
                continue
            try:
                image_data = cls.get_remote_image(cleaned_input.get("url"))
                image_data.content_type = "image/jpg"
                image_data.name = "image.jpg"
                validate_image_file(image_data, "image")

                instance = models.ProductImage(product=product,
                                               image=image_data, alt=cleaned_input.get("alt", ""))

                cls.clean_instance(info, instance)
                instances.append(instance)
            except ValidationError as exc:
                cls.add_indexes_to_errors(index, exc, errors)
        return instances

    @classmethod
    @transaction.atomic
    def update_or_create_variant_stocks(cls,info,  variant, stocks_data, warehouses):
        stocks = []
        for stock_data, warehouse in zip(stocks_data, warehouses):
            stock, _ = warehouse_models.Stock.objects.get_or_create(
                product_variant=variant, warehouse=warehouse
            )
            stock.quantity = stock_data["quantity"]
            stocks.append(stock)
        warehouse_models.Stock.objects.bulk_update(stocks, ["quantity"])

    @classmethod
    def update_or_create_variants(cls,info,  product, cleaned_inputs, errors):
        variants = []
        for index, cleaned_input in enumerate(cleaned_inputs):
            if not cleaned_input:
                continue
            try:
                if cleaned_input.get("id") is not None:
                    instance = cleaned_input.get("id")
                else:
                    instance = models.ProductVariant()


                cleaned_input["product"] = product
                instance = cls.construct_instance(instance, cleaned_input)
                cls.clean_instance(info, instance)
                variants.append(instance)
            except ValidationError as exc:
                cls.add_indexes_to_errors(index, exc, errors)
        return variants
        
        

    @classmethod
    @transaction.atomic
    def save_images(cls, info, instances, cleaned_inputs):
        assert len(instances) == len(
            cleaned_inputs
        ), "There should be the same number of instances and cleaned inputs."
        for instance, cleaned_input in zip(instances, cleaned_inputs):
            instance.save()

    @classmethod
    @transaction.atomic
    def save_variants(cls, info, instances, cleaned_inputs):
        assert len(instances) == len(
            cleaned_inputs
        ), "There should be the same number of instances and cleaned inputs."
        for instance, cleaned_input in zip(instances, cleaned_inputs):
            instance.save()
            attributes = cleaned_input.get("attributes")
            if attributes:
                AttributeAssignmentMixin.save(instance, attributes)
                instance.name = generate_name_for_variant(instance)
                instance.save(update_fields=["name"])      

            stocks = cleaned_input.get("stocks")
            if stocks:
                warehouse_ids = [stock["warehouse"] for stock in stocks]
                warehouses = cls.get_nodes_or_error(
                    warehouse_ids, "warehouse", only_type=Warehouse
                )
                cls.update_or_create_variant_stocks(info, instance, stocks, warehouses)

    @classmethod
    @transaction.atomic
    def save(cls, info, instance, cleaned_input):
        errors = defaultdict(list)
        instance.save()

        variants_input = cleaned_input.get("variants", None)
        if variants_input is not None:
            variants = cls.update_or_create_variants(info, instance, variants_input, errors)
        

        if errors:
            raise ValidationError(errors)
        
        if variants and instance.base_variant is not None:
            instance.base_variant.delete()
            instance.base_variant = None
            instance.save()

        cls.save_variants(info, variants, variants_input)

        update_product_minimal_variant_price_task.delay(instance.pk)

        images_input = cleaned_input.get("images", None)
        images = None
        if images_input is not None:
            images = cls.create_images(info, images_input, instance, errors)

        if errors:
            raise ValidationError(errors)

        if images:
            cls.save_images(info, images, images_input)



    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        collections = cleaned_data.get("collections", None)
        if collections is not None:
            instance.collections.set(collections)

        tags = cleaned_data.get("tags", None)
        if tags is not None:
            instance.tags.set(*tags, clear=True)

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        response = super().perform_mutation(_root, info, **data)
        info.context.plugins.product_created(response.product)
        return response


class ProductUpdate(ProductCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a product to update.")
        input = ProductInput(
            required=True, description="Fields required to update a product."
        )

    class Meta:
        description = "Updates an existing product."
        model = models.Product
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def clean_sku(cls, product_type, cleaned_input):
        input_sku = cleaned_input.get("sku")
        if (
            not product_type.has_variants
            and input_sku
            and models.ProductVariant.objects.filter(sku=input_sku).exists()
        ):
            raise ValidationError(
                {
                    "sku": ValidationError(
                        "Product with this SKU already exists.",
                        code=ProductErrorCode.ALREADY_EXISTS,
                    )
                }
            )

    @classmethod
    @transaction.atomic
    def save(cls, info, instance, cleaned_input):
        super().save(info, instance, cleaned_input)





class ProductDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a product to delete.")

    class Meta:
        description = "Deletes a product."
        model = models.Product
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductUpdateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.Product
        description = "Update public metadata for product."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductClearMeta(ClearMetaBaseMutation):
    class Meta:
        description = "Clears public metadata item for product."
        model = models.Product
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductUpdatePrivateMeta(UpdateMetaBaseMutation):
    class Meta:
        description = "Update private metadata for product."
        model = models.Product
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductClearPrivateMeta(ClearMetaBaseMutation):
    class Meta:
        description = "Clears private metadata item for product."
        model = models.Product
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"





class ProductVariantCreate(ModelMutation):
    class Arguments:
        input = ProductVariantInput(
            required=True, description="Fields required to create a product variant."
        )

    class Meta:
        description = "Creates a new variant for a product."
        model = models.ProductVariant
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def clean_attributes(
        cls, attributes: dict
    ) -> T_INPUT_MAP:
        attributes = AttributeAssignmentMixin.clean_input(
            attributes, models.Attribute.objects.all(), is_variant=True
        )
        return attributes

    @classmethod
    def validate_duplicated_attribute_values(
        cls, attributes, used_attribute_values, instance=None
    ):
        attribute_values = defaultdict(list)
        for used_attribute_value in used_attribute_values:
            values = [value.lower() for value in used_attribute_value]
            used_attribute_value = values

        for attribute in attributes:
            values = [value.lower() for value in attribute.values]
            attribute_values[attribute.id].extend(values)

        if attribute_values in used_attribute_values:
            raise ValidationError(
                "Duplicated attribute values for product variant.",
                ProductErrorCode.DUPLICATED_INPUT_ITEM,
            )
        else:
            used_attribute_values.append(attribute_values)

    @classmethod
    def clean_input(
        cls, info, instance: models.ProductVariant, data: dict, input_cls=None
    ):
        cleaned_input = super().clean_input(info, instance, data)

        weight = cleaned_input.get("weight")
        if weight and weight.value < 0:
            raise ValidationError(
                {
                    "weight": ValidationError(
                        "Product variant can't have negative weight.",
                        code=ProductErrorCode.INVALID.value,
                    )
                }
            )

        if "cost_price" in cleaned_input:
            cost_price = cleaned_input.pop("cost_price")
            if cost_price and cost_price < 0:
                raise ValidationError(
                    {
                        "costPrice": ValidationError(
                            "Product price cannot be lower than 0.",
                            code=ProductErrorCode.INVALID.value,
                        )
                    }
                )
            cleaned_input["cost_price_amount"] = cost_price

        price = cleaned_input.get("price")
        if price is None and instance.price is None:
            raise ValidationError(
                {
                    "price": ValidationError(
                        "Variant price is required.",
                        code=ProductErrorCode.REQUIRED.value,
                    )
                }
            )

        if "price" in cleaned_input:
            price = cleaned_input.pop("price")
            if price is not None and price < 0:
                raise ValidationError(
                    {
                        "price": ValidationError(
                            "Product price cannot be lower than 0.",
                            code=ProductErrorCode.INVALID.value,
                        )
                    }
                )
            cleaned_input["price_amount"] = price

        stocks = cleaned_input.get("stocks")
        if stocks:
            cls.check_for_duplicates_in_stocks(stocks)

        # Attributes are provided as list of `AttributeValueInput` objects.
        # We need to transform them into the format they're stored in the
        # `Product` model, which is HStore field that maps attribute's PK to
        # the value's PK.
        attributes = cleaned_input.get("attributes")
        if attributes:
            if instance.product_id is not None:
                # If the variant is getting updated,
                # simply retrieve the associated product type
                used_attribute_values = get_used_variants_attribute_values(
                    instance.product
                )
            else:
                # If the variant is getting created, no product type is associated yet,
                # retrieve it from the required "product" input field
                used_attribute_values = get_used_variants_attribute_values(
                    cleaned_input["product"]
                )

            try:
                cls.validate_duplicated_attribute_values(
                    attributes, used_attribute_values, instance
                )
                cleaned_input["attributes"] = cls.clean_attributes(
                    attributes
                )
            except ValidationError as exc:
                raise ValidationError({"attributes": exc})
        else:
            if instance.product_id is not None:
                # If the variant is getting updated,
                # check if it has attributes, and if it is not the base variant
                # to make sure all variants have attributes
                if not instance.attributes  and instance.product.base_variant != variant:
                    raise ValidationError(
                        {
                            "attributes": ValidationError(
                                "None base variants must have attributes",
                                code=ProductErrorCode.INVALID.value,
                            )
                        }
                    )

            else:
                # If the variant is getting created,
                # and doesn't has attributes
                 raise ValidationError(
                        {
                            "attributes": ValidationError(
                                "None base variants must have attributes",
                                code=ProductErrorCode.INVALID.value,
                            )
                        }
                    )
    

        return cleaned_input

    @classmethod
    def check_for_duplicates_in_stocks(cls, stocks_data):
        warehouse_ids = [stock["warehouse"] for stock in stocks_data]
        duplicates = get_duplicated_values(warehouse_ids)
        if duplicates:
            error_msg = "Duplicated warehouse ID: {}".format(", ".join(duplicates))
            raise ValidationError(
                {"stocks": ValidationError(error_msg, code=ProductErrorCode.UNIQUE)}
            )

    @classmethod
    def get_instance(cls, info, **data):
        """Prefetch related fields that are needed to process the mutation.

        If we are updating an instance and want to update its attributes,
        # prefetch them.
        """

        object_id = data.get("id")
        if object_id and data.get("attributes"):

            return cls.get_node_or_error(
                info, object_id, only_type="ProductVariant", qs=qs
            )

        return super().get_instance(info, **data)

    @classmethod
    @transaction.atomic()
    def save(cls, info, instance, cleaned_input):
        instance.save()

        if  not instance.product.base_variant == instance:
            instance.product.base_variant.delete()
            instance.product.base_variant = None
            instance.product.save()

        # Recalculate the "minimal variant price" for the parent product
        update_product_minimal_variant_price_task.delay(instance.product_id)
        stocks = cleaned_input.get("stocks")
        if stocks:
            cls.create_variant_stocks(instance, stocks)

        attributes = cleaned_input.get("attributes")
        if attributes:
            AttributeAssignmentMixin.save(instance, attributes)
            instance.name = generate_name_for_variant(instance)
            instance.save(update_fields=["name"])

    @classmethod
    def create_variant_stocks(cls, variant, stocks):
        warehouse_ids = [stock["warehouse"] for stock in stocks]
        warehouses = cls.get_nodes_or_error(
            warehouse_ids, "warehouse", only_type=Warehouse
        )
        create_stocks(variant, stocks, warehouses)


class ProductVariantUpdate(ProductVariantCreate):
    class Arguments:
        id = graphene.ID(
            required=True, description="ID of a product variant to update."
        )
        input = ProductVariantInput(
            required=True, description="Fields required to update a product variant."
        )

    class Meta:
        description = "Updates an existing variant for product."
        model = models.ProductVariant
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def validate_duplicated_attribute_values(
        cls, attributes, used_attribute_values, instance=None
    ):
        # Check if the variant is getting updated,
        # and the assigned attributes do not change
        if instance.id is not None:
            assigned_attributes = get_used_attribute_values_for_variant(instance)
            input_attribute_values = defaultdict(list)

            for assigned_attribute in assigned_attributes:
                values = [value.lower() for value in assigned_attribute]
                assigned_attribute = values

            for attribute in attributes:
                values = [value.lower() for value in attribute.values]
                input_attribute_values[attribute.id].extend(values)
            if input_attribute_values == assigned_attributes:
                return
        # if assigned attributes is getting updated run duplicated attribute validation
        super().validate_duplicated_attribute_values(attributes, used_attribute_values)


class ProductVariantDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(
            required=True, description="ID of a product variant to delete."
        )

    class Meta:
        description = "Deletes a product variant."
        model = models.ProductVariant
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        if not cls.check_permissions(info.context):
            raise PermissionDenied()

        node_id = data.get("id")
        instance = cls.get_node_or_error(info, node_id, only_type=ProductVariant)

        if instance:
            cls.clean_instance(info, instance)

        db_id = instance.id
        delete_variants([db_id])

        instance.id = db_id
        return cls.success_response(instance)


class ProductVariantUpdateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.ProductVariant
        description = "Update public metadata for product variant."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductVariantClearMeta(ClearMetaBaseMutation):
    class Meta:
        model = models.ProductVariant
        description = "Clears public metadata for product variant."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductVariantUpdatePrivateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.ProductVariant
        description = "Update private metadata for product variant."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductVariantClearPrivateMeta(ClearMetaBaseMutation):
    class Meta:
        model = models.ProductVariant
        description = "Clears private metadata for product variant."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductTypeInput(graphene.InputObjectType):
    name = graphene.String(description="Name of the product type.")
    slug = graphene.String(description="Product type slug.")
    has_variants = graphene.Boolean(
        description=(
            "Determines if product of this type has multiple variants. This option "
            "mainly simplifies product management in the dashboard. There is always at "
            "least one variant created under the hood."
        )
    )
    product_attributes = graphene.List(
        graphene.ID,
        description="List of attributes shared among all product variants.",
        name="productAttributes",
    )
    variant_attributes = graphene.List(
        graphene.ID,
        description=(
            "List of attributes used to distinguish between different variants of "
            "a product."
        ),
        name="variantAttributes",
    )
    is_shipping_required = graphene.Boolean(
        description="Determines if shipping is required for products of this variant."
    )
    is_digital = graphene.Boolean(
        description="Determines if products are digital.", required=False
    )
    weight = WeightScalar(description="Weight of the ProductType items.")
    tax_code = graphene.String(description="Tax rate for enabled tax gateway.")


class ProductTypeCreate(ModelMutation):
    class Arguments:
        input = ProductTypeInput(
            required=True, description="Fields required to create a product type."
        )

    class Meta:
        description = "Creates a new product type."
        model = models.ProductType
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)

        weight = cleaned_input.get("weight")
        if weight and weight.value < 0:
            raise ValidationError(
                {
                    "weight": ValidationError(
                        "Product type can't have negative weight.",
                        code=ProductErrorCode.INVALID,
                    )
                }
            )

        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = ProductErrorCode.REQUIRED.value
            raise ValidationError({"slug": error})

        # FIXME  tax_rate logic should be dropped after we remove tax_rate from input
        tax_rate = cleaned_input.pop("tax_rate", "")
        if tax_rate:
            instance.store_value_in_metadata(
                {"vatlayer.code": tax_rate, "description": tax_rate}
            )
            info.context.plugins.assign_tax_code_to_object_meta(instance, tax_rate)

        tax_code = cleaned_input.pop("tax_code", "")
        if tax_code:
            info.context.plugins.assign_tax_code_to_object_meta(instance, tax_code)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)
        product_attributes = cleaned_data.get("product_attributes")
        variant_attributes = cleaned_data.get("variant_attributes")
        if product_attributes is not None:
            instance.product_attributes.set(product_attributes)
        if variant_attributes is not None:
            instance.variant_attributes.set(variant_attributes)


class ProductTypeUpdate(ProductTypeCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a product type to update.")
        input = ProductTypeInput(
            required=True, description="Fields required to update a product type."
        )

    class Meta:
        description = "Updates an existing product type."
        model = models.ProductType
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def save(cls, info, instance, cleaned_input):
        variant_attr = cleaned_input.get("variant_attributes")
        if variant_attr:
            variant_attr = set(variant_attr)
            variant_attr_ids = [attr.pk for attr in variant_attr]
            update_variants_names.delay(instance.pk, variant_attr_ids)
        super().save(info, instance, cleaned_input)


class ProductTypeDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a product type to delete.")

    class Meta:
        description = "Deletes a product type."
        model = models.ProductType
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

class ProductTypeUpdateMeta(UpdateMetaBaseMutation):
    class Meta:
        model = models.ProductType
        description = "Update public metadata for product type."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductTypeClearMeta(ClearMetaBaseMutation):
    class Meta:
        description = "Clears public metadata for product type."
        model = models.ProductType
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = True
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductTypeUpdatePrivateMeta(UpdateMetaBaseMutation):
    class Meta:
        description = "Update private metadata for product type."
        model = models.ProductType
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductTypeClearPrivateMeta(ClearMetaBaseMutation):
    class Meta:
        description = "Clears private metadata for product type."
        model = models.ProductType
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        public = False
        error_type_class = ProductError
        error_type_field = "product_errors"


class VendorInput(graphene.InputObjectType):
    name = graphene.String(description="Name of the product type.")
    slug = graphene.String(description="Product type slug.")


class VendorCreate(ModelMutation):
    class Arguments:
        input = VendorInput(
            required=True, description="Fields required to create a vendor."
        )

    class Meta:
        description = "Creates a new vendor."
        model = models.Vendor
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)

        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = ProductErrorCode.REQUIRED.value
            raise ValidationError({"slug": error})

        return cleaned_input

class VendorUpdate(VendorCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a vendor to update.")
        input = VendorInput(
            required=True, description="Fields required to update a vendor."
        )

    class Meta:
        description = "Updates an existing vendor."
        model = models.Vendor
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def save(cls, info, instance, cleaned_input):
        super().save(info, instance, cleaned_input)


class VendorDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a vendor to delete.")

    class Meta:
        description = "Deletes a vendor."
        model = models.Vendor
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"


class ProductImageCreateInput(graphene.InputObjectType):
    alt = graphene.String(description="Alt text for an image.")
    image = Upload(
        required=True, description="Represents an image file in a multipart request."
    )
    product = graphene.ID(
        required=True, description="ID of an product.", name="product"
    )


class ProductImageCreate(BaseMutation):
    product = graphene.Field(Product)
    image = graphene.Field(ProductImage)

    class Arguments:
        input = ProductImageCreateInput(
            required=True, description="Fields required to create a product image."
        )

    class Meta:
        description = (
            "Create a product image. This mutation must be sent as a `multipart` "
            "request. More detailed specs of the upload format can be found here: "
            "https://github.com/jaydenseric/graphql-multipart-request-spec"
        )
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        data = data.get("input")
        product = cls.get_node_or_error(
            info, data["product"], field="product", only_type=Product
        )
        image_data = info.context.FILES.get(data["image"])
        validate_image_file(image_data, "image")

        image = product.images.create(image=image_data, alt=data.get("alt", ""))
        create_product_thumbnails.delay(image.pk)
        return ProductImageCreate(product=product, image=image)


class ProductImageUpdateInput(graphene.InputObjectType):
    alt = graphene.String(description="Alt text for an image.")


class ProductImageUpdate(BaseMutation):
    product = graphene.Field(Product)
    image = graphene.Field(ProductImage)

    class Arguments:
        id = graphene.ID(required=True, description="ID of a product image to update.")
        input = ProductImageUpdateInput(
            required=True, description="Fields required to update a product image."
        )

    class Meta:
        description = "Updates a product image."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        image = cls.get_node_or_error(info, data.get("id"), only_type=ProductImage)
        product = image.product
        alt = data.get("input").get("alt")
        if alt is not None:
            image.alt = alt
            image.save(update_fields=["alt"])
        return ProductImageUpdate(product=product, image=image)


class ProductImageReorder(BaseMutation):
    product = graphene.Field(Product)
    images = graphene.List(ProductImage)

    class Arguments:
        product_id = graphene.ID(
            required=True,
            description="Id of product that images order will be altered.",
        )
        images_ids = graphene.List(
            graphene.ID,
            required=True,
            description="IDs of a product images in the desired order.",
        )

    class Meta:
        description = "Changes ordering of the product image."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, product_id, images_ids):
        product = cls.get_node_or_error(
            info, product_id, field="product_id", only_type=Product
        )
        if len(images_ids) != product.images.count():
            raise ValidationError(
                {
                    "order": ValidationError(
                        "Incorrect number of image IDs provided.",
                        code=ProductErrorCode.INVALID,
                    )
                }
            )

        images = []
        for image_id in images_ids:
            image = cls.get_node_or_error(
                info, image_id, field="order", only_type=ProductImage
            )
            if image and image.product != product:
                raise ValidationError(
                    {
                        "order": ValidationError(
                            "Image %(image_id)s does not belong to this product.",
                            code=ProductErrorCode.NOT_PRODUCTS_IMAGE,
                            params={"image_id": image_id},
                        )
                    }
                )
            images.append(image)

        for order, image in enumerate(images):
            image.sort_order = order
            image.save(update_fields=["sort_order"])

        return ProductImageReorder(product=product, images=images)


class ProductImageDelete(BaseMutation):
    product = graphene.Field(Product)
    image = graphene.Field(ProductImage)

    class Arguments:
        id = graphene.ID(required=True, description="ID of a product image to delete.")

    class Meta:
        description = "Deletes a product image."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        image = cls.get_node_or_error(info, data.get("id"), only_type=ProductImage)
        image_id = image.id
        image.delete()
        image.id = image_id
        return ProductImageDelete(product=image.product, image=image)


class VariantImageAssign(BaseMutation):
    product_variant = graphene.Field(ProductVariant)
    image = graphene.Field(ProductImage)

    class Arguments:
        image_id = graphene.ID(
            required=True, description="ID of a product image to assign to a variant."
        )
        variant_id = graphene.ID(required=True, description="ID of a product variant.")

    class Meta:
        description = "Assign an image to a product variant."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, image_id, variant_id):
        image = cls.get_node_or_error(
            info, image_id, field="image_id", only_type=ProductImage
        )
        variant = cls.get_node_or_error(
            info, variant_id, field="variant_id", only_type=ProductVariant
        )
        if image and variant:
            # check if the given image and variant can be matched together
            image_belongs_to_product = variant.product.images.filter(
                pk=image.pk
            ).first()
            if image_belongs_to_product:
                image.variant_images.create(variant=variant)
            else:
                raise ValidationError(
                    {
                        "image_id": ValidationError(
                            "This image doesn't belong to that product.",
                            code=ProductErrorCode.NOT_PRODUCTS_IMAGE,
                        )
                    }
                )
        return VariantImageAssign(product_variant=variant, image=image)


class VariantImageUnassign(BaseMutation):
    product_variant = graphene.Field(ProductVariant)
    image = graphene.Field(ProductImage)

    class Arguments:
        image_id = graphene.ID(
            required=True,
            description="ID of a product image to unassign from a variant.",
        )
        variant_id = graphene.ID(required=True, description="ID of a product variant.")

    class Meta:
        description = "Unassign an image from a product variant."
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        error_type_class = ProductError
        error_type_field = "product_errors"

    @classmethod
    def perform_mutation(cls, _root, info, image_id, variant_id):
        image = cls.get_node_or_error(
            info, image_id, field="image_id", only_type=ProductImage
        )
        variant = cls.get_node_or_error(
            info, variant_id, field="variant_id", only_type=ProductVariant
        )

        try:
            variant_image = models.VariantImage.objects.get(
                image=image, variant=variant
            )
        except models.VariantImage.DoesNotExist:
            raise ValidationError(
                {
                    "image_id": ValidationError(
                        "Image is not assigned to this variant.",
                        code=ProductErrorCode.NOT_PRODUCTS_IMAGE,
                    )
                }
            )
        else:
            variant_image.delete()

        return VariantImageUnassign(product_variant=variant, image=image)
