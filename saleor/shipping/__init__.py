class DeliveryConditionType:
    PRICE_BASED = "price"
    WEIGHT_BASED = "weight"

    CHOICES = [
        (PRICE_BASED, "Price based shipping"),
        (WEIGHT_BASED, "Weight based shipping"),
    ]

class ShippingMethodType:
    PRICE_BASED = "price"
    WEIGHT_BASED = "weight"
    GENERAL = "GENERAL"

    CHOICES = [
        (PRICE_BASED, "Price based shipping"),
        (WEIGHT_BASED, "Weight based shipping"),
        (GENERAL, "General shipping"),
    ]

class LocalDeliveryType:
    RADIUS_BASED = "raduis"
    POSTAL_CODE_BASED = "postal"

    CHOICES = [
        (RADIUS_BASED, "Radius based local delivery"),
        (POSTAL_CODE_BASED, "Postal code based local delivery"),
    ]
