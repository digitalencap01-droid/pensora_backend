import json
import re
from pathlib import Path
from urllib.parse import urlparse

import nh3
from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    select_autoescape,
)
from markdown_it import MarkdownIt
from markupsafe import Markup

from app.schemas.article import (
    ArticleSection,
    ArticleSource,
)
from app.schemas.html import (
    HTMLRenderRequest,
    HTMLRenderResult,
)


class HTMLService:
    def __init__(self) -> None:
        self.template_directory = Path(
            "app/templates"
        )

        self.output_directory = Path(
            "output"
        )

        self.jinja = Environment(
            loader=FileSystemLoader(
                self.template_directory
            ),
            autoescape=select_autoescape(
                enabled_extensions=(
                    "html",
                    "xml",
                ),
                default_for_string=True,
                default=True,
            ),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.markdown = MarkdownIt(
            "js-default",
            {
                "html": False,
                "linkify": False,
                "typographer": True,
            },
        )

        self.cleaner = nh3.Cleaner(
            tags={
                "p",
                "br",
                "strong",
                "em",
                "b",
                "i",
                "u",
                "s",
                "del",
                "blockquote",
                "ul",
                "ol",
                "li",
                "h3",
                "h4",
                "h5",
                "h6",
                "a",
                "sup",
                "code",
                "pre",
                "hr",
                "table",
                "thead",
                "tbody",
                "tfoot",
                "tr",
                "th",
                "td",
            },
            attributes={
                "a": {
                    "href",
                    "title",
                },
                "code": {
                    "class",
                },
                "th": {
                    "colspan",
                    "rowspan",
                    "scope",
                },
                "td": {
                    "colspan",
                    "rowspan",
                },
            },
            url_schemes={
                "http",
                "https",
                "mailto",
            },
            url_relative="deny",
            link_rel=(
                "noopener noreferrer"
            ),
            strip_comments=True,
        )

    def render(
        self,
        request: HTMLRenderRequest,
    ) -> HTMLRenderResult:
        source_lookup = (
            self._build_source_lookup(
                request.article.sources
            )
        )

        # Shared across introduction/sections/conclusion so citation
        # numbers are assigned in reading order — the first source
        # cited becomes [1], regardless of its position in the
        # original research list.
        citation_order: list[str] = []

        introduction_html = (
            self._render_markdown(
                request
                .article
                .introduction
                .content_markdown,
                source_lookup,
                citation_order,
            )
        )

        sections = []
        toc = []

        for section in (
            request.article.sections
        ):
            anchor_id = (
                self._safe_anchor_id(
                    section.section_id
                )
            )

            section_html = (
                self._render_markdown(
                    section.content_markdown,
                    source_lookup,
                    citation_order,
                )
            )

            sections.append(
                {
                    "section_id": (
                        section.section_id
                    ),
                    "anchor_id": anchor_id,
                    "heading": (
                        section.heading
                    ),
                    "html": section_html,
                    "images": (
                        self._section_images(section)
                    ),
                }
            )

            toc.append(
                {
                    "id": anchor_id,
                    "heading": (
                        section.heading
                    ),
                }
            )

        conclusion_html = (
            self._render_markdown(
                request
                .article
                .conclusion
                .content_markdown,
                source_lookup,
                citation_order,
            )
        )

        # Only sources actually cited somewhere in the body end up
        # in the bibliography — a real, verifiable source list
        # rather than a dump of every link research turned up.
        sources = [
            {
                "number": number,
                "source_id": source_id,
                "title": (
                    source_lookup[source_id].title
                    or source_lookup[source_id].domain
                    or source_lookup[source_id].url
                ),
                "url": source_lookup[source_id].url,
                "domain": source_lookup[source_id].domain,
                "is_link": source_lookup[
                    source_id
                ].url.startswith(
                    ("http://", "https://")
                ),
            }
            for number, source_id
            in enumerate(citation_order, start=1)
        ]

        featured_image_url = None
        featured_image_alt = None

        if request.seo.open_graph.images:
            featured_image_url = (
                request
                .seo
                .open_graph
                .images[0]
            )
            # Alt text is optional in the generation form — don't
            # let a blank alt silently hide a selected image.
            featured_image_alt = (
                request.featured_image_alt
                or request.article.h1
            )

        json_ld_json = (
            self._safe_json_ld(
                request.seo.json_ld
            )
        )

        template_context = {
            "article": request.article,
            "seo": request.seo,
            "language_code": (
                request.language_code
            ),
            "text_direction": (
                request.text_direction
            ),
            "introduction_html": (
                introduction_html
            ),
            "sections": sections,
            "conclusion_html": (
                conclusion_html
            ),
            "toc": toc,
            "sources": sources,
            "include_sources": (
                request.include_sources
            ),
            "featured_image_url": (
                featured_image_url
            ),
            "featured_image_alt": (
                featured_image_alt
            ),
            "json_ld_json": Markup(
                json_ld_json
            ),
        }

        body_template = (
            self.jinja.get_template(
                "partials/"
                "article_body.html"
            )
        )

        article_html = (
            body_template.render(
                **template_context
            )
        )

        full_template = (
            self.jinja.get_template(
                "article.html"
            )
        )

        full_html = (
            full_template.render(
                **template_context
            )
        )

        filename = self._build_filename(
            request.seo.slug
        )

        relative_path = None

        if request.save_file:
            relative_path = (
                self._save_html_file(
                    filename=filename,
                    html=full_html,
                )
            )

        return HTMLRenderResult(
            filename=filename,
            full_html=full_html,
            article_html=article_html,
            saved=request.save_file,
            relative_path=relative_path,
        )

    def _build_source_lookup(
        self,
        sources: list[ArticleSource],
    ) -> dict[str, ArticleSource]:
        return {
            source.source_id: source
            for source in sources
            if self._is_safe_url(source.url)
        }

    def _render_markdown(
        self,
        markdown_content: str,
        source_lookup: dict[str, ArticleSource],
        citation_order: list[str],
    ) -> Markup:
        # Citations are substituted after Markdown rendering (not
        # before): the MarkdownIt instance runs with html=False, so
        # a raw <sup> tag inserted into the Markdown source would
        # get escaped as literal text instead of parsed as HTML.
        # "[S1]" itself has no special meaning to the Markdown
        # parser, so it survives rendering as plain text unchanged.
        rendered_html = (
            self.markdown.render(
                markdown_content
            )
        )

        rendered_html = (
            self._replace_citations(
                rendered_html,
                source_lookup,
                citation_order,
            )
        )

        clean_html = (
            self.cleaner.clean(
                rendered_html
            )
        )

        return Markup(
            clean_html
        )

    _CITATION_RUN_PATTERN = re.compile(
        r"(?:\[S\d+\])+"
    )
    _CITATION_ID_PATTERN = re.compile(
        r"\[(S\d+)\]"
    )

    def _replace_citations(
        self,
        content: str,
        source_lookup: dict[str, ArticleSource],
        citation_order: list[str],
    ) -> str:
        def replace_run(
            match: re.Match,
        ) -> str:
            source_ids = (
                self._CITATION_ID_PATTERN.findall(
                    match.group(0)
                )
            )

            numbers: list[int] = []

            for source_id in source_ids:
                if source_id not in source_lookup:
                    continue

                if source_id not in citation_order:
                    citation_order.append(source_id)

                number = (
                    citation_order.index(source_id)
                    + 1
                )

                if number not in numbers:
                    numbers.append(number)

            if not numbers:
                return ""

            marker = ",".join(
                str(number) for number in numbers
            )

            return f"<sup>{marker}</sup>"

        return self._CITATION_RUN_PATTERN.sub(
            replace_run,
            content,
        )

    def _safe_json_ld(
        self,
        json_ld: dict,
    ) -> str:
        serialized = json.dumps(
            json_ld,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )

        serialized = (
            serialized
            .replace(
                "<",
                "\\u003c",
            )
            .replace(
                ">",
                "\\u003e",
            )
            .replace(
                "&",
                "\\u0026",
            )
        )

        return serialized

    def _safe_anchor_id(
        self,
        value: str,
    ) -> str:
        cleaned = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "-",
            value.strip(),
        )

        cleaned = cleaned.strip(
            "-"
        )

        if not cleaned:
            return "section"

        return cleaned.lower()

    def _build_filename(
        self,
        slug: str,
    ) -> str:
        cleaned = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "-",
            slug,
        )

        cleaned = cleaned.strip(
            "-"
        ).lower()

        if not cleaned:
            raise ValueError(
                "Invalid article slug."
            )

        return f"{cleaned}.html"

    def _save_html_file(
        self,
        filename: str,
        html: str,
    ) -> str:
        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            self.output_directory
            / filename
        )

        file_path.write_text(
            html,
            encoding="utf-8",
        )

        return str(
            file_path.as_posix()
        )

    def _is_safe_url(
        self,
        url: str,
    ) -> bool:
        parsed = urlparse(
            url
        )

        if parsed.scheme in {"http", "https"}:
            return bool(parsed.netloc)

        # doc://<document_id>/chunk/<n> — an internal locator into an
        # uploaded document (app/services/document_research_service.py),
        # not a real web address. Shown in the sources list as plain
        # text, never as a clickable <a href>.
        if parsed.scheme == "doc":
            return bool(parsed.netloc)

        return False

    def _is_renderable_image_url(
        self,
        url: str,
    ) -> bool:
        parsed = urlparse(url)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    def _section_images(
        self,
        section: ArticleSection,
    ) -> list[dict]:
        images = []

        for index, url in enumerate(section.image_urls):
            if not self._is_renderable_image_url(url):
                continue

            alt = (
                section.image_alts[index]
                if index < len(section.image_alts)
                else section.heading
            )

            images.append(
                {
                    "url": url,
                    "alt": alt or section.heading,
                }
            )

        return images


html_service = HTMLService()
