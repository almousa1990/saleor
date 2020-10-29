from graphene import relay
import graphene
from ...theme import models
from ..core.connection import CountableDjangoObjectType

class ThemeAsset(CountableDjangoObjectType):

    class Meta:
        description = (
            "Theme file"
        )
        only_fields = [
            "name",
            "path"
        ]
        interfaces = [relay.Node]
        model = models.ThemeAsset

class ThemeFile(CountableDjangoObjectType):
    name = graphene.String(description="Theme file name."
        )

    class Meta:
        description = (
            "Theme file"
        )
        only_fields = [
            "path",
            "content",
        ]
        interfaces = [relay.Node]
        model = models.ThemeFile

    @staticmethod
    def resolve_name(root: models.ThemeFile, _info):
        return root.name


class Theme(CountableDjangoObjectType):
    files = graphene.List(
            ThemeFile, description="List of theme files."
        )

    assets = graphene.List(
            ThemeAsset, description="List of theme files."
        )

    class Meta:
        description = (
            "A theme in the shop "
        )
        only_fields = [
            "name",
            "slug",
            "id",
        ]
        interfaces = [relay.Node]
        model = models.Theme

    @staticmethod
    def resolve_files(root: models.Theme, _info):
        return root.files.all()

    @staticmethod
    def resolve_assets(root: models.Theme, _info):
        return root.assets.all()