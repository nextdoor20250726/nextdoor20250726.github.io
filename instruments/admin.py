from django.contrib import admin

from .models import Category, Instrument


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    list_filter = ("parent",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("parent__name", "name")


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "wikidata_id", "source_url", "created_at", "updated_at")
    list_filter = ("category", "created_at", "updated_at")
    search_fields = (
        "name",
        "wikidata_id",
        "category__name",
        "introduction_md",
        "history_md",
        "timbre_description",
        "source_url",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("category",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("基本資料", {"fields": ("name", "category")}),
        ("百科內容 Markdown", {"fields": ("introduction_md", "history_md")}),
        ("媒體、聲音與來源", {"fields": ("wikidata_id", "source_url", "exploded_view_image", "timbre_description", "listen_link")}),
        ("時間資訊", {"fields": ("created_at", "updated_at")}),
    )
