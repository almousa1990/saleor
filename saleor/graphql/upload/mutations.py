import graphene
from django.core.exceptions import ValidationError

from ...core import JobStatus
from ...core.permissions import OrderPermissions
from ...upload import models
from ...invoice.emails import send_invoice
from ...invoice.error_codes import InvoiceErrorCode
from ...order import OrderStatus, events as order_events
from ..core.mutations import ModelDeleteMutation, ModelMutation, BaseMutation
from ..core.types.common import UploadError
from ..invoice.types import Invoice
from ..order.types import Order
from ..upload.enums import StagedUploadHttpMethodType, StagedUploadTargetGenerateUploadResource
from ..upload.types import StagedUploadsCreatePayload, StagedMediaUploadTarget
from ..core.utils import get_duplicates_ids, validate_image_file


class StagedUploadInput(graphene.InputObjectType):
    file_size = graphene.Int(description="Size of the file to upload, in bytes. This is required for VIDEO and MODEL_3D resources.")
    filename = graphene.String(description="Media filename.", required=True)
    http_method = graphene.Field(StagedUploadHttpMethodType)
    mime_type = graphene.String(description="Media MIME type.", required=True)
    resource = graphene.Field(StagedUploadTargetGenerateUploadResource, required=True)

class StagedUploadsCreate(BaseMutation):
    staged_targets = graphene.List(StagedMediaUploadTarget)

    class Arguments:
        input = graphene.List(
            StagedUploadInput, required=True, description="Input for the mutation includes information needed to generate staged upload targets."
        )
        
    class Meta:
        description = "Return type for `stagedUploadsCreate` mutation."
        permissions = (OrderPermissions.MANAGE_ORDERS,)
        error_type_class = UploadError
        error_type_field = "upload_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        data = data.get("input")
        image_data = info.context.FILES.get(data["image"])
        validate_image_file(image_data, "image")
