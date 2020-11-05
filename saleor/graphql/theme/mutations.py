import graphene
from django.core.exceptions import ValidationError
from zipfile import ZipFile, is_zipfile

from ..core.mutations import BaseMutation
from ...theme import models
from ..core.types import Upload
from .types import Theme
from django.core.files.base import ContentFile
from django.core.files import File
import json
from django.db import transaction
from pathlib import Path
import magic

class ThemeUpload(BaseMutation):
    class Arguments:
        id = graphene.ID(description="ID of a theme to upload.", required=True)
        file = Upload(required=True)

    class Meta:
        description = "Uploads a theme file."
        model = models.Theme

    @classmethod
    @transaction.atomic()
    def perform_mutation_old(cls, _root, info, **data):
        zip_file = info.context.FILES.get(data.get("file"))
        assert is_zipfile(zip_file)

        with ZipFile(zip_file, 'r') as theme_zip_file:
            with theme_zip_file.open('config/settings_data.json') as settings_data_file:
                settings_data_file_content = settings_data_file.read()
                settings_data_json = json.loads(settings_data_file_content)

            with theme_zip_file.open('config/settings_schema.json') as settings_schema_file:
                settings_schema_file_content = settings_schema_file.read()
                settings_schema_json = json.loads(settings_schema_file_content)
            theme_info = settings_schema_json[0]
            theme = models.Theme(name=theme_info['theme_name'], author=theme_info['theme_author'], version=theme_info['theme_version'], documentation_url=theme_info['theme_documentation_url'], support_url=theme_info['theme_support_url'], settings_data=settings_data_json, settings_schema=settings_schema_json)
            theme.save()

            for name in theme_zip_file.namelist():
                if not name.endswith('/'):

                    with theme_zip_file.open(name) as theme_file:
                        if name.endswith('.liquid'):
                            file_content = theme_file.read()
                            theme_template = models.ThemeTemplate(
                                theme=theme, path=name, content=file_content.decode("utf-8"))
                            theme_template.save()
                        
                        elif name.startswith('assets/'):
                            theme_asset = models.ThemeAsset(
                                theme=theme, path=name, content_file=File(theme_file))
                            theme_asset.save()
                            
                        elif name.startswith('locales/'):
                            file_content = theme_file.read()

                            try:
                                json_content = json.loads(file_content)
                            except ValueError as e:
                                raise ValidationError(
                                    {"locale": "Incorrect format."})

                            language_code = Path(name).stem
                            
                            is_default = False
                            if language_code.endswith('.default'):
                                is_default = True
                                language_code = language_code.rstrip(".default")

                            theme_locale = models.ThemeLocale(
                                theme=theme, language_code=language_code, content=json_content, default=is_default)
                            theme_locale.save()

        results = []

    @classmethod
    @transaction.atomic()
    def perform_mutation(cls, _root, info, **data):
        zip_file = info.context.FILES.get(data.get("file"))
        assert is_zipfile(zip_file)

        with ZipFile(zip_file, 'r') as theme_zip_file:
            with theme_zip_file.open('config/settings_schema.json') as settings_schema_file:
                settings_schema_file_content = settings_schema_file.read()
                settings_schema_json = json.loads(settings_schema_file_content)

            theme_info = settings_schema_json[0]
            theme = models.Theme(name=theme_info['theme_name'], author=theme_info['theme_author'], version=theme_info['theme_version'],
                                 documentation_url=theme_info['theme_documentation_url'], support_url=theme_info['theme_support_url'], settings_schema=settings_schema_json)
            theme.save()

            for name in theme_zip_file.namelist():
                if not name.endswith('/'):

                    with theme_zip_file.open(name) as theme_file:
                        file_content = theme_file.read()
                        content_type = magic.from_buffer(file_content, mime=True)

                        theme_file_instance = models.ThemeFile(
                            theme=theme, path=name, content_type=content_type, content_file=File(theme_file))

                        if content_type in ["text/plain", "text/html", "application/json"]:
                            theme_file_instance.raw_content = file_content.decode(
                                "utf-8")

                        theme_file_instance.save()

        results = []
