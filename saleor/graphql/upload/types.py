import graphene

from ...invoice import models
from ..core.connection import CountableDjangoObjectType
from ..core.types.common import Job
from ..meta.types import ObjectWithMetadata


class StagedUploadParameter(graphene.ObjectType):
    name = graphene.String(description="Parameter name.")
    value = graphene.String(description="Parameter value.")

    class Meta:
        description = "Upload parameter of a Media."



class MutationsStagedUploadTargetGenerateUploadParameter(graphene.ObjectType):
    name = graphene.String(description="The upload parameter name.")
    value = graphene.String(description="The upload parameter value.")

    class Meta:
        description = "A signed upload parameter for uploading an asset to Saleor."


class ImageUploadParameter(graphene.ObjectType):
    name = graphene.String(description="Parameter name.")
    value = graphene.String(description="Parameter value.")

    class Meta:
        description = "Upload parameter of an image."


class StagedMediaUploadTarget(graphene.ObjectType):
    id = graphene.ID(description="ID.")
    parameters = graphene.List(StagedUploadParameter, description="Parameters of the media to be uploaded")
    resource_url = graphene.String(description="The url to be passed as the original_source for the product create media mutation input.")
    url = graphene.String(description="Media URL.")

    class Meta:
        description = "Staged media target information."

class StagedUploadTarget(graphene.ObjectType):
    parameters = graphene.List(ImageUploadParameter, description="Parameters of an image to be uploaded")
    url = graphene.String(description="Image URL.")

    class Meta:
        description = "Staged target information."


class StagedUploadTargetGeneratePayload(graphene.ObjectType):
    parameters = graphene.List(MutationsStagedUploadTargetGenerateUploadParameter, description="The signed parameters that can be used to upload the asset")
    url = graphene.String(description="The signed URL where the asset can be uploaded.")

    class Meta:
        description = "Return type for `stagedUploadTargetGenerate` mutation."


class StagedUploadTargetsGeneratePayload(graphene.ObjectType):
    urls = graphene.List(StagedUploadTarget, description="The staged upload targets that were generated")

    class Meta:
        description = "Return type for `stagedUploadTargetsGenerate` mutation."


class StagedUploadsCreatePayload(graphene.ObjectType):
    staged_targets = graphene.List(StagedMediaUploadTarget, description="The staged upload targets that were generated")

    class Meta:
        description = "Return type for `stagedUploadsCreate` mutation."

