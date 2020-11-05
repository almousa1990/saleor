import json
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List

import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError


from ...theme.models import ThemeFile

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from ...product.models import Attribute, ProductVariant

translatable_settings = ['title', 'name']

def get_section_settings_data(name):
    raw_settings_data = ThemeFile.objects.get(path="config/settings_data.json").raw_content
    json_settings_data = json.loads(raw_settings_data)
    section_settings_data = [value for key, value in json_settings_data.get(
        'current').get('sections').items() if key == name][0]

    return section_settings_data


def get_section_schema(raw_content):
    schema_matches = re.findall(
        r"{% *schema *%}([\s\S]*){% *endschema *%}", raw_content)
    raw_schema = next(iter(schema_matches), None)
    json_schema = json.loads(raw_schema)
    
    return json_schema

def get_translated_setting_value(value, language_code='en'):
    if isinstance(value, dict):
        value = value.get(language_code)
    
    return value

def merge_section_settings(schema_settings, data_settings):
    settings = defaultdict(list)

    for setting in schema_settings:
        key = setting.get('id')
        value = data_settings.get(key)

        if not value:
            value = setting.get('default')

        if key in translatable_settings:
            value = get_translated_setting_value(value)


        settings[key] = value
    return settings

def merge_block_settings(schema_settings, data_settings):
    settings = defaultdict(list)

    for setting in data_settings:
        key = setting.get('id')
        value = data_settings.get(key)

        if not value:
            value = setting.get('default')

        if key in translatable_settings:
            value = get_translated_setting_value(value)


        settings[key] = value
    return settings

def get_section_settings(name, raw_content):
    section_schema = get_section_schema(raw_content)
    section_settings_data = get_section_settings_data(name)
    settings = merge_section_settings(section_schema.get('settings'), section_settings_data.get('settings'))

    return settings

def get_section_blocks(section_name, raw_content):
    section_schema = get_section_schema(raw_content)
    section_settings_data = get_section_settings_data(section_name)
    
    blocks = defaultdict(list)
    for key, block in section_settings_data.get('blocks').items():
        block_settings_data = section_settings_data.get('blocks').get(section_settings_data.get('block_order')[index]) # ensure you get settings per blocks order
        blocks[key] = {"type": block.get('type'), "settings": merge_theme_settings(block.get('settings'), block_settings_data)}

    return blocks
