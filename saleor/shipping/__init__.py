class DeliveryConditionType:
    PRICE_BASED = "price"
    WEIGHT_BASED = "weight"

    CHOICES = [
        (PRICE_BASED, "Price based shipping"),
        (WEIGHT_BASED, "Weight based shipping"),
    ]

class DeliveryMethodType:
    LOCAL = "LOCAL"
    NONE = "NONE"
    PICK_UP = "PICK_UP"
    RETAIL = "RETAIL"
    SHIPPING = "SHIPPING"

    CHOICES = [
        (LOCAL, "Local delivery method"),
        (NONE, "No delivery method"),
        (PICK_UP, "Pick-up delivery method"),
        (RETAIL, "Retail delivery method represents items delivered immediately in a retail store"),
        (SHIPPING, "Shipping delivery method"),
    ]

class DeliveryMethodType:
    PRICE_BASED = "price"
    WEIGHT_BASED = "weight"
    GENERAL = "GENERAL"

    CHOICES = [
        (PRICE_BASED, "Price based delivery"),
        (WEIGHT_BASED, "Weight based delivery"),
        (GENERAL, "General delivery"),
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
