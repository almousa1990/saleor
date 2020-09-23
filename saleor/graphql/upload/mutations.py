import graphene
from django.core.exceptions import ValidationError

from ...core.permissions import ProductPermissions
from ..core.mutations import BaseMutation
from ..core.types.common import UploadError
from ...upload import models
from ..upload.enums import StagedUploadHttpMethodType, StagedUploadTargetGenerateUploadResource
from ..upload.types import StagedUploadsCreatePayload, StagedUploadTarget, StagedMediaUploadTarget
from ..core.utils import validate_image_file
from ..core.types import Upload


class StagedUploadInput(graphene.InputObjectType):
    file = Upload(
        required=True, description="Represents a file in a multipart request."
    )
    file_size = graphene.Int(
        description="Size of the file to upload, in bytes. This is required for VIDEO and MODEL_3D resources.")
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
        permissions = (ProductPermissions.MANAGE_PRODUCTS,)
        model = models.StagedTarget
        error_type_class = UploadError
        error_type_field = "upload_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        files = data.get("input")
        results = []
        for file in files:
            content_data = info.context.FILES.get(file["file"])
            validate_image_file(content_data, "image")
            staged_file = models.StagedTarget(content_file=content_data)
            staged_file.save()
            results.append(StagedMediaUploadTarget(id=staged_file.pk, resource_url=info.context.build_absolute_uri(
                staged_file.content_file.url), url=info.context.build_absolute_uri(staged_file.content_file.url)))
        return StagedUploadsCreate(staged_targets=results)
