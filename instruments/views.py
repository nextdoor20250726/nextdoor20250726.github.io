import bleach
import markdown

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Instrument


ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union(
    {
        "p",
        "pre",
        "code",
        "h1",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "blockquote",
        "strong",
        "em",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "hr",
        "br",
        "img",
    }
)

ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
}


def render_markdown(md_text):
    raw_html = markdown.markdown(
        md_text or "",
        extensions=["extra", "toc", "tables", "fenced_code", "nl2br"],
        output_format="html5",
    )
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


def home(request):
    categories = (
        Category.objects.filter(parent__isnull=True)
        .annotate(instrument_count=Count("instruments"))
        .prefetch_related("children")
    )
    featured_instruments = Instrument.objects.select_related("category")[:8]
    return render(
        request,
        "instruments/home.html",
        {
            "categories": categories,
            "featured_instruments": featured_instruments,
        },
    )


def instrument_list(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    instruments = Instrument.objects.select_related("category")

    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        category_ids = [selected_category.id, *selected_category.get_descendant_ids()]
        instruments = instruments.filter(category_id__in=category_ids)

    if query:
        instruments = instruments.filter(
            Q(name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(introduction_md__icontains=query)
            | Q(history_md__icontains=query)
            | Q(timbre_description__icontains=query)
        )

    paginator = Paginator(instruments, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "instruments/instrument_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "categories": Category.objects.all(),
            "selected_category": selected_category,
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    category_ids = [category.id, *category.get_descendant_ids()]
    instruments = Instrument.objects.select_related("category").filter(category_id__in=category_ids)
    paginator = Paginator(instruments, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "instruments/category_detail.html",
        {
            "category": category,
            "page_obj": page_obj,
        },
    )


def instrument_detail(request, pk):
    instrument = get_object_or_404(Instrument.objects.select_related("category"), pk=pk)
    return render(
        request,
        "instruments/instrument_detail.html",
        {
            "instrument": instrument,
            "introduction_html": render_markdown(instrument.introduction_md),
            "history_html": render_markdown(instrument.history_md),
        },
    )
