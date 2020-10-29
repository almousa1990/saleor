import graphene

from ...country import models


def resolve_country(info, code=None):
    assert code, "No code provided."
    return models.Country.objects.filter(code=code).first()


def resolve_countries(info, **_kwargs):
    return models.Country.objects.all()
