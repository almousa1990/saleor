from django.db import models


class StagedTarget(models.Model):
    content_file = models.FileField(upload_to="staged_files", null=True)
