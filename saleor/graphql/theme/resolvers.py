import graphene
import os
from django.core.exceptions import ValidationError
from ...theme import models


def resolve_theme(info, slug=None):
    assert slug, "No slug provided."
    return models.Theme.objects.filter(slug=slug).first()


def resolve_themes(info, **_kwargs):
    return models.Theme.objects.all()

def resolve_theme_template(info, theme_slug=None, name=None):
    if theme_slug is None or name is None:
        raise ValidationError(
            "Theme slug and file name must be provided."
        )
    filename, file_extension = os.path.splitext(name)

    if not file_extension:
        filename = filename + ".liquid"
    else:
        filename = filename + file_extension
    

    return models.ThemeTemplate.objects.filter(theme__slug=theme_slug).filter(path__contains=filename).first()


def resolve_theme_asset(info, theme_slug=None, path=None):
    if theme_slug is None or path is None:
        raise ValidationError(
            "Theme slug and path must be provided."
        )
    return models.ThemeAsset.objects.filter(theme__slug=theme_slug).filter(path=path).first()

def resolve_theme_section(info, theme_slug=None, name=None):
    if theme_slug is None or name is None:
        raise ValidationError(
            "Theme slug and file name must be provided."
        )
    filename, file_extension = os.path.splitext(name)

    if not file_extension:
        filename = filename + ".liquid"
    else:
        filename = filename + file_extension
    

    return models.ThemeFile.objects.filter(theme__slug=theme_slug).filter(path__contains=filename).first()

