from graphene import relay
import graphene
from ...theme import models
from ..core.connection import CountableDjangoObjectType

class ThemeAsset(CountableDjangoObjectType):
    name = graphene.String(description="Theme asset name.")
    url = graphene.String(description="Theme asset URL.")

    class Meta:
        description = (
            "Theme asset"
        )
        only_fields = [
            "path"
        ]
        interfaces = [relay.Node]
        model = models.ThemeAsset
    
    @staticmethod
    def resolve_url(root: models.ThemeAsset, _info):
        return root.content_file.url

    @staticmethod
    def resolve_name(root: models.ThemeAsset, _info):
        return root.name


class ThemeTemplate(CountableDjangoObjectType):
    name = graphene.String(description="Theme template name."
        )

    class Meta:
        description = (
            "Theme template"
        )
        only_fields = [
            "path",
            "content",
        ]
        interfaces = [relay.Node]
        model = models.ThemeTemplate

    @staticmethod
    def resolve_name(root: models.ThemeTemplate, _info):
        return root.name

class ThemeSetting2(graphene.ObjectType):
    type = graphene.String()
    id = graphene.String()
    label = graphene.String()
    placeholder = graphene.String()
    default = graphene.String()
    info = graphene.String()
    value= graphene.String()

class ThemeSettingsCategory(graphene.ObjectType):
    name = graphene.String()
    settings = graphene.List(ThemeSetting2)
    
class ThemeSetting(graphene.ObjectType):
    key = graphene.String()
    value = graphene.String()

class ThemeSectionBlock(graphene.ObjectType):
    name = graphene.String()
    type = graphene.String()
    settings = graphene.List(ThemeSetting)


class ThemeSection(graphene.ObjectType):
    name = graphene.String()
    type = graphene.String()
    section_class = graphene.String()
    section_tag = graphene.String()
    settings = graphene.List(ThemeSetting)
    blocks = graphene.List(ThemeSectionBlock)

class ThemeCurrentSettingData(graphene.ObjectType):
    sections = graphene.List(ThemeSection)
    content_for_index = graphene.List(graphene.String)
    settings = graphene.List(ThemeSetting)

    
class Theme(CountableDjangoObjectType):
    theme_settings_categories = graphene.List(ThemeSettingsCategory)

    templates = graphene.List(
            ThemeTemplate, description="List of theme templates."
        )

    assets = graphene.List(
            ThemeAsset, description="List of theme assets."
        )

    class Meta:
        description = (
            "A theme in the shop "
        )
        only_fields = [
            "name",
            "slug",
            "id",
            "version",
            "author",
            "documentation_url",
            "support_url",
            "settings_data",
            "settings_schema"

        ]
        interfaces = [relay.Node]
        model = models.Theme

    @staticmethod
    def resolve_templates(root: models.Theme, _info):
        return root.templates.all()

    @staticmethod
    def resolve_assets(root: models.Theme, _info):
        return root.assets.all()

    @staticmethod
    def resolve_settings2(root: models.Theme, _info):
        sections_data = root.settings_data.get('current').pop('sections')
        sections = []
        for section_key, section_data in sections_data.items():
            section_settings = [ThemeSetting(k, v)
                                for k, v in section_data.get('settings').items()]
            blocks = []
            if section_data.get('blocks'):
                for block_key, block_data in section_data.get('blocks').items():
                    block_settings = [ThemeSetting(k, v)
                                    for k, v in block_data.get('settings').items()]
                    block = ThemeBlock(name=block_key, type=block_data.get(
                        'type'), settings=block_settings)
                    blocks.append(block)

            section = ThemeSection(name=section_key, type=section_data.get(
                'type'), settings=section_settings, blocks=blocks, block_order=section_data.get('block_order'))
            sections.append(section)

        # return sections
        content_for_index = root.settings_data.get('current').pop('content_for_index')
        settings = [ThemeSetting(k, v) for k, v in root.settings_data.get('current').items()]
        return ThemeCurrentSettingData(settings=settings, sections=sections, content_for_index=content_for_index)

    @staticmethod
    def resolve_theme_settings_categories(root: models.Theme, _info):
        settings_categories = root.settings_schema[1:]
        settings_categories_list = []
        for setting_categry in settings_categories:
            if isinstance(setting_categry.get('name'), dict):
                name = setting_categry.get('name').get('en')
            else:
                name = setting_categry.get('name')
            
            settings = []
            for setting in setting_categry.get('settings'):
                if root.settings_data.get('current').get(setting.get('id')):
                    value = root.settings_data.get('current').get(setting.get('id'))
                else:
                    value = setting.get('default')
                settings.append(ThemeSetting(id=setting.get('id'), type=setting.get('type'), default=setting.get(
                    'default'), value=value))


            settings_categories_list.append(ThemeSettingsCategory(
                name=name, settings=settings))
        return settings_categories_list
