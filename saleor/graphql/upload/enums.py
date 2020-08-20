import graphene
from django_countries import countries

from ...account import CustomerEvents
from ...checkout import AddressType
from ...graphql.core.enums import to_enum
from ..core.utils import str_to_enum


class StagedUploadHttpMethodType(graphene.Enum):
    POST = "POST"
    PUT = "PUT"

class StagedUploadTargetGenerateUploadResource(graphene.Enum):
    TIMELINE = "TIMELINE"
    PRODUCT_IMAGE = "PRODUCT_IMAGE"
    COLLECTION_IMAGE = "COLLECTION_IMAGE"
    SHOP_IMAGE = "SHOP_IMAGE"
    VIDEO = "VIDEO"
    MODEL_3D = "MODEL_3D"
    IMAGE = "IMAGE"