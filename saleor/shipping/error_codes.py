from enum import Enum


class ShippingErrorCode(Enum):
    ALREADY_EXISTS = "already_exists"
    GRAPHQL_ERROR = "graphql_error"
    INVALID = "invalid"
    MAX_LESS_THAN_MIN = "max_less_than_min"
    NOT_FOUND = "not_found"
    REQUIRED = "required"
    UNIQUE = "unique"
    DUPLICATED_INPUT_ITEM = "duplicated_input_item"
    DUPLICATED_COUNTRY_IN_GROUP = "duplicated_country_in_group"
    DEFAULT_SHIPPING_PROFILE = "default_shipping_profile"
