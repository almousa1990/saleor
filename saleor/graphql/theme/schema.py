import graphene

from ..core.fields import FilterInputConnectionField
from .filters import ThemeFilterInput
from .resolvers import resolve_theme, resolve_themes, resolve_theme_file, resolve_theme_asset
from .types import Theme, ThemeAsset, ThemeFile

from .mutations import (
    ThemeUpload
)


class ThemeQueries(graphene.ObjectType):
    theme = graphene.Field(
        Theme,
        slug=graphene.String(description="The slug of the theme."),
        description="Look up a theme by slug.",
    )
    themes = FilterInputConnectionField(
        Theme,
        filter=ThemeFilterInput(description="Filtering options for themes."),
        description="List of themes.",
    )
    theme_asset = graphene.Field(
        ThemeAsset,
        theme_slug=graphene.String(description="Theme slug."),
        path=graphene.String(description="Asset path."),
        description="Look up a theme asset.",
    )
    theme_file = graphene.Field(
        ThemeFile,
        theme_slug=graphene.String(description="Theme slug."),
        name=graphene.String(description="File name."),
        description="Look up a theme file.",
    )
    def resolve_theme(self, info, slug=None):
        return resolve_theme(info, slug)

    def resolve_themes(self, info, **kwargs):
        return resolve_themes(info, **kwargs)

    def resolve_theme_file(self, info, theme_slug=None, name=None):
        return resolve_theme_file(info, theme_slug, name)

    def resolve_theme_asset(self, info, theme_slug=None, path=None):
        return resolve_theme_asset(info, theme_slug, path)

class ThemeMutations(graphene.ObjectType):
    theme_upload = ThemeUpload.Field()
