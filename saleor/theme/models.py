from django.db import models
import os



class Theme(models.Model):

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=False)

    version = models.CharField(max_length=10)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

class ThemeFile(models.Model):
    theme = models.ForeignKey(Theme, related_name="files", on_delete=models.CASCADE)
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
