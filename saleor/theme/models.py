from django.db import models
import os



class Theme(models.Model):

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=False)

    version = models.CharField(max_length=10, null=True)
    author = models.CharField(max_length=128, null=True)
    documentation_url = models.CharField(max_length=200, null=True)
    support_url = models.CharField(max_length=200, null=True)
    settings_data = models.JSONField(default=dict)
    settings_schema = models.JSONField(default=dict)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

class ThemeFile(models.Model):
    theme = models.ForeignKey(Theme, related_name="files", on_delete=models.CASCADE)
    path = models.CharField(max_length=256)
    content_file = models.FileField(upload_to="theme_files", null=True)
    raw_content = models.TextField(null=True)
    content_type = models.CharField(null=True, max_length=100)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("pk", )
        unique_together = (("path", "theme"),)

    def __str__(self):
        return os.path.basename(self.path)

    @property
    def name(self):
        return os.path.basename(self.path)



class ThemeTemplate(models.Model):
    theme = models.ForeignKey(Theme, related_name="templates", on_delete=models.CASCADE)
    path = models.CharField(max_length=256)
    content = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("pk", )
        unique_together = (("path", "theme"),)

    def __str__(self):
        return os.path.basename(self.path)

    @property
    def name(self):
        return os.path.basename(self.path)


class ThemeAsset(models.Model):
    theme = models.ForeignKey(Theme, related_name="assets", on_delete=models.CASCADE)
    path = models.CharField(max_length=256)
    content_file = models.FileField(upload_to="theme_assets", null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("pk", )
        unique_together = (("path", "theme"),)

    def __str__(self):
        return os.path.basename(self.path)
        
    @property
    def name(self):
        return os.path.basename(self.path)



class ThemeLocale(models.Model):
    theme = models.ForeignKey(Theme, related_name="locales", on_delete=models.CASCADE)
    default = models.BooleanField(default=False)
    language_code = models.CharField(max_length=10)
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("pk", )
        unique_together = (("language_code", "theme"),)

    def __str__(self):
        return self.language_code
        