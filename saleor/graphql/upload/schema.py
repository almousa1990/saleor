import graphene

from .mutations import (
    StagedUploadsCreate
)


class UploadMutations(graphene.ObjectType):
    staged_uploads_create = StagedUploadsCreate.Field()
