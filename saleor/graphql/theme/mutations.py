import graphene
from django.core.exceptions import ValidationError
from zipfile import ZipFile, is_zipfile

from ..core.mutations import BaseMutation
from ...theme import models
from ..core.types import Upload
from .types import Theme
from django.core.files.base import ContentFile
from django.core.files import File


class ThemeUpload(BaseMutation):
    class Arguments:
        id = graphene.ID(description="ID of a theme to upload.", required=True)
        file = Upload(required=True)

    class Meta:
        description = "Uploads a theme file."
        model = models.Theme

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        theme = cls.get_node_or_error(info, data.get("id"), Theme)

        zip_file = info.context.FILES.get(data.get("file"))
        assert is_zipfile(zip_file)

        with ZipFile(zip_file, 'r') as theme_zip_file:
            for name in theme_zip_file.namelist():
                if not name.endswith('/'):

                    with theme_zip_file.open(name) as f:
                            if name.endswith('.liquid'):
                                file_content = f.read()
                                theme_file = models.ThemeFile(theme=theme, path=name, content=file_content.decode("utf-8"))
                                theme_file.save()
                            else:
                                theme_asset = models.ThemeAsset(theme=theme, path=name, content_file=File(f))
                                theme_asset.save()

        results = []