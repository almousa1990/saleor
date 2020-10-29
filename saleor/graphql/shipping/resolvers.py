from ...shipping import models


def resolve_shipping_zones(info):
    return models.ShippingZone.objects.all()


def resolve_shipping_profiles(info):
    return models.ShippingProfile.objects.all()


def resolve_shipping_methods(info):
    return models.ShippingMethod.objects.all()