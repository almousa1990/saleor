import json
import re
import graphene
from ..core.fields import FilterInputConnectionField
from .filters import ThemeFilterInput
from .resolvers import resolve_theme, resolve_themes, resolve_theme_template, resolve_theme_asset, resolve_theme_section
from .types import Theme, ThemeAsset, ThemeTemplate, ThemeSection
from .utils import get_section_settings, get_section_blocks
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
    theme_template = graphene.Field(
        ThemeTemplate,
        theme_slug=graphene.String(description="Theme slug."),
        name=graphene.String(description="Template name."),
        description="Look up a theme template.",
    )
    theme_section = graphene.Field(
        ThemeSection,
        theme_slug=graphene.String(description="Theme slug."),
        name=graphene.String(description="Template name."),
        description="Look up a theme template.",
    )
    def resolve_theme(self, info, slug=None):
        return resolve_theme(info, slug)

    def resolve_themes(self, info, **kwargs):
        return resolve_themes(info, **kwargs)

    def resolve_theme_template(self, info, theme_slug=None, name=None):
        return resolve_theme_template(info, theme_slug, name)

    def resolve_theme_section(self, info, theme_slug=None, name=None):
        section = resolve_theme_section(info, theme_slug, name)
        settings = get_section_settings(name, section.raw_content)
        blocks = get_section_blocks(name, section.raw_content)
        return ThemeSection()



    def resolve_theme_asset(self, info, theme_slug=None, path=None):
        return resolve_theme_asset(info, theme_slug, path)

class ThemeMutations(graphene.ObjectType):
    theme_upload = ThemeUpload.Field()
