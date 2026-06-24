from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField("分類名稱", max_length=120)
    slug = models.SlugField("URL Slug", max_length=140, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="上層分類",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )
    description = models.TextField("分類描述", blank=True)

    class Meta:
        verbose_name = "樂器分類"
        verbose_name_plural = "樂器分類"
        ordering = ["parent__name", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name

    def get_absolute_url(self):
        return reverse("instrument_category", kwargs={"slug": self.slug})

    def get_descendant_ids(self):
        descendant_ids = []
        nodes = list(self.children.all())
        while nodes:
            node = nodes.pop()
            descendant_ids.append(node.id)
            nodes.extend(node.children.all())
        return descendant_ids


class Instrument(models.Model):
    name = models.CharField("樂器名稱", max_length=160)
    wikidata_id = models.CharField("Wikidata ID", max_length=32, unique=True, blank=True, null=True)
    category = models.ForeignKey(
        Category,
        verbose_name="分類",
        related_name="instruments",
        on_delete=models.PROTECT,
    )
    introduction_md = models.TextField("介紹 Markdown")
    history_md = models.TextField("歷史背景 Markdown", blank=True)
    exploded_view_image = models.CharField(
        "樂器拆解圖 URL 或檔案路徑",
        max_length=500,
        blank=True,
    )
    timbre_description = models.TextField("音色文字描述", blank=True)
    listen_link = models.URLField("聆聽連結", max_length=500, blank=True)
    source_url = models.URLField("資料來源", max_length=500, blank=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        verbose_name = "樂器"
        verbose_name_plural = "樂器"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["wikidata_id"]),
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("instrument_detail", kwargs={"pk": self.pk})
