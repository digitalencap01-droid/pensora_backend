import json
from urllib.parse import urlparse

from slugify import slugify

from app.prompts.seo import SEO_METADATA_PROMPT
from app.schemas.seo import (
    OpenGraphMetadata,
    SEOCheck,
    SEOMetadataAI,
    SEORequest,
    SEOResult,
    SchemaType,
    TwitterMetadata,
)
from app.services.openai_service import (
    openai_service,
)


class SEOService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def generate_seo(
        self,
        request: SEORequest,
    ) -> SEOResult:
        metadata = await self._generate_metadata(
            request
        )

        slug = self._build_slug(
            request
        )

        canonical_url = self._build_canonical_url(
            request=request,
            slug=slug,
        )

        schema_type = self._resolve_schema_type(
            request
        )

        robots_meta = self._build_robots_meta(
            request
        )

        image_urls = [
            str(url)
            for url in request.featured_image_urls
        ]

        thumbnail_url = (
            str(request.thumbnail_image_url)
            if request.thumbnail_image_url
            else (image_urls[0] if image_urls else None)
        )

        open_graph = OpenGraphMetadata(
            title=metadata.social_title.strip(),
            description=(
                metadata
                .social_description
                .strip()
            ),
            url=canonical_url,
            type="article",
            site_name=request.site_name,
            images=image_urls,
        )

        twitter = TwitterMetadata(
            card=(
                "summary_large_image"
                if image_urls
                else "summary"
            ),
            title=metadata.social_title.strip(),
            description=(
                metadata
                .social_description
                .strip()
            ),
            images=image_urls,
        )

        json_ld = self._build_json_ld(
            request=request,
            schema_type=schema_type,
            canonical_url=canonical_url,
            image_urls=image_urls,
        )

        checks = self._run_checks(
            request=request,
            seo_title=metadata.seo_title,
            meta_description=(
                metadata.meta_description
            ),
            canonical_url=canonical_url,
            schema_type=schema_type,
            json_ld=json_ld,
            image_urls=image_urls,
        )

        readiness_score = (
            self._calculate_readiness_score(
                checks
            )
        )

        return SEOResult(
            seo_title=metadata.seo_title.strip(),
            meta_description=(
                metadata
                .meta_description
                .strip()
            ),
            slug=slug,
            canonical_url=canonical_url,
            robots_meta=robots_meta,
            open_graph=open_graph,
            twitter=twitter,
            thumbnail_url=thumbnail_url,
            schema_type=schema_type,
            json_ld=json_ld,
            checks=checks,
            readiness_score=readiness_score,
        )

    async def _generate_metadata(
        self,
        request: SEORequest,
    ) -> SEOMetadataAI:
        payload = {
            "article": {
                "topic": request.article.topic,
                "title": request.article.title,
                "h1": request.article.h1,
                "language": (
                    request.article.language
                ),
                "introduction": (
                    request
                    .article
                    .introduction
                    .content_markdown
                ),
                "sections": [
                    {
                        "heading": section.heading,
                        "summary": section.summary,
                    }
                    for section
                    in request.article.sections
                ],
                "conclusion": (
                    request
                    .article
                    .conclusion
                    .content_markdown
                ),
            },
            "strategy": {
                "primary_keyword": (
                    request
                    .brief
                    .primary_keyword
                ),
                "search_intent": (
                    request.brief.search_intent
                ),
                "content_angle": (
                    request.brief.content_angle
                ),
                "target_reader": (
                    request.brief.target_reader
                ),
                "reader_outcome": (
                    request.brief.reader_outcome
                ),
            },
            "site_name": request.site_name,
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=SEO_METADATA_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=SEOMetadataAI,
            store=False,
        )

        metadata = response.output_parsed

        if metadata is None:
            raise ValueError(
                "OpenAI did not return valid "
                "SEO metadata."
            )

        return metadata

    def _build_slug(
        self,
        request: SEORequest,
    ) -> str:
        source = (
            request.slug_override
            or request.brief.primary_keyword
            or request.article.h1
        )

        slug = slugify(
            source,
            lowercase=True,
            separator="-",
        )

        if not slug:
            raise ValueError(
                "Unable to generate article slug."
            )

        return slug

    def _build_canonical_url(
        self,
        request: SEORequest,
        slug: str,
    ) -> str:
        site_url = str(
            request.site_url
        ).rstrip("/")

        prefix = (
            request
            .article_path_prefix
            .strip()
        )

        prefix = (
            "/"
            + prefix.strip("/")
            if prefix.strip("/")
            else ""
        )

        return (
            f"{site_url}"
            f"{prefix}"
            f"/{slug}/"
        )

    def _resolve_schema_type(
        self,
        request: SEORequest,
    ) -> SchemaType:
        if request.schema_type_override:
            return request.schema_type_override

        article_type = (
            request.brief.article_type
        )

        if article_type == "news":
            return "NewsArticle"

        if article_type == "blog":
            return "BlogPosting"

        return "Article"

    def _build_robots_meta(
        self,
        request: SEORequest,
    ) -> str | None:
        if request.indexable:
            return None

        return "noindex,follow"

    def _build_json_ld(
        self,
        request: SEORequest,
        schema_type: SchemaType,
        canonical_url: str,
        image_urls: list[str],
    ) -> dict:
        json_ld: dict = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "headline": request.article.h1,
        }

        if image_urls:
            json_ld["image"] = image_urls

        if request.authors:
            json_ld["author"] = [
                self._author_json_ld(author)
                for author in request.authors
            ]

        if request.date_published:
            json_ld["datePublished"] = (
                request
                .date_published
                .isoformat()
            )

        if request.date_modified:
            json_ld["dateModified"] = (
                request
                .date_modified
                .isoformat()
            )

        publisher_name = (
            request.publisher_name
            or request.site_name
        )

        publisher: dict = {
            "@type": "Organization",
            "name": publisher_name,
        }

        if request.publisher_url:
            publisher["url"] = str(
                request.publisher_url
            )

        if request.publisher_logo_url:
            publisher["logo"] = {
                "@type": "ImageObject",
                "url": str(
                    request.publisher_logo_url
                ),
            }

        json_ld["publisher"] = publisher

        json_ld["mainEntityOfPage"] = {
            "@type": "WebPage",
            "@id": canonical_url,
        }

        return json_ld

    def _author_json_ld(
        self,
        author,
    ) -> dict:
        data = {
            "@type": author.author_type,
            "name": author.name,
        }

        if author.url:
            data["url"] = str(
                author.url
            )

        return data

    def _run_checks(
        self,
        request: SEORequest,
        seo_title: str,
        meta_description: str,
        canonical_url: str,
        schema_type: SchemaType,
        json_ld: dict,
        image_urls: list[str],
    ) -> list[SEOCheck]:
        checks: list[SEOCheck] = []

        checks.append(
            self._check_title(
                request=request,
                seo_title=seo_title,
            )
        )

        checks.append(
            self._check_meta_description(
                meta_description
            )
        )

        checks.append(
            self._check_canonical(
                canonical_url
            )
        )

        checks.append(
            self._check_indexability(
                request
            )
        )

        checks.append(
            self._check_authors(
                request
            )
        )

        checks.append(
            self._check_dates(
                request
            )
        )

        checks.append(
            self._check_images(
                image_urls
            )
        )

        checks.append(
            self._check_section_images(
                request
            )
        )

        checks.append(
            self._check_structured_data(
                schema_type=schema_type,
                json_ld=json_ld,
            )
        )

        checks.append(
            self._check_citations(
                request
            )
        )

        checks.append(
            self._check_word_count(
                request
            )
        )

        return checks

    def _check_title(
        self,
        request: SEORequest,
        seo_title: str,
    ) -> SEOCheck:
        title = seo_title.strip()

        if not title:
            return SEOCheck(
                check_id="seo_title",
                status="fail",
                message=(
                    "SEO title is missing."
                ),
                weight=15,
            )

        primary_keyword = (
            request
            .brief
            .primary_keyword
            .casefold()
        )

        title_normalized = (
            title.casefold()
        )

        if (
            primary_keyword
            not in title_normalized
        ):
            return SEOCheck(
                check_id="seo_title",
                status="warning",
                message=(
                    "SEO title is present but "
                    "does not contain the exact "
                    "primary topic phrase. "
                    "This is acceptable when the "
                    "title is more natural."
                ),
                weight=15,
            )

        return SEOCheck(
            check_id="seo_title",
            status="pass",
            message=(
                "SEO title is present and "
                "reflects the primary topic."
            ),
            weight=15,
        )

    def _check_meta_description(
        self,
        meta_description: str,
    ) -> SEOCheck:
        if not meta_description.strip():
            return SEOCheck(
                check_id="meta_description",
                status="fail",
                message=(
                    "Meta description is missing."
                ),
                weight=10,
            )

        return SEOCheck(
            check_id="meta_description",
            status="pass",
            message=(
                "Meta description is present."
            ),
            weight=10,
        )

    def _check_canonical(
        self,
        canonical_url: str,
    ) -> SEOCheck:
        parsed = urlparse(
            canonical_url
        )

        if (
            parsed.scheme not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):
            return SEOCheck(
                check_id="canonical",
                status="fail",
                message=(
                    "Canonical URL is invalid."
                ),
                weight=15,
            )

        return SEOCheck(
            check_id="canonical",
            status="pass",
            message=(
                "Canonical URL is configured."
            ),
            weight=15,
        )

    def _check_indexability(
        self,
        request: SEORequest,
    ) -> SEOCheck:
        if not request.indexable:
            return SEOCheck(
                check_id="indexability",
                status="warning",
                message=(
                    "Page is configured with "
                    "noindex."
                ),
                weight=15,
            )

        return SEOCheck(
            check_id="indexability",
            status="pass",
            message=(
                "Page is configured to allow "
                "indexing."
            ),
            weight=15,
        )

    def _check_authors(
        self,
        request: SEORequest,
    ) -> SEOCheck:
        if not request.authors:
            return SEOCheck(
                check_id="author",
                status="warning",
                message=(
                    "No article author has been "
                    "provided."
                ),
                weight=10,
            )

        return SEOCheck(
            check_id="author",
            status="pass",
            message=(
                "Article author metadata is "
                "available."
            ),
            weight=10,
        )

    def _check_dates(
        self,
        request: SEORequest,
    ) -> SEOCheck:
        published = request.date_published
        modified = request.date_modified

        if not published:
            return SEOCheck(
                check_id="dates",
                status="warning",
                message=(
                    "Publication date is not "
                    "available yet."
                ),
                weight=10,
            )

        if (
            modified
            and modified < published
        ):
            return SEOCheck(
                check_id="dates",
                status="fail",
                message=(
                    "Modified date cannot be "
                    "earlier than publication "
                    "date."
                ),
                weight=10,
            )

        return SEOCheck(
            check_id="dates",
            status="pass",
            message=(
                "Article date metadata is "
                "consistent."
            ),
            weight=10,
        )

    def _check_images(
        self,
        image_urls: list[str],
    ) -> SEOCheck:
        if not image_urls:
            return SEOCheck(
                check_id="featured_image",
                status="warning",
                message=(
                    "No representative article "
                    "image has been provided."
                ),
                weight=10,
            )

        return SEOCheck(
            check_id="featured_image",
            status="pass",
            message=(
                "Representative article image "
                "metadata is available."
            ),
            weight=10,
        )

    def _check_section_images(
        self,
        request: SEORequest,
    ) -> SEOCheck:
        sections = request.article.sections
        word_count = (
            request.article.total_word_count
        )

        # Short articles read fine with just the featured image —
        # in-body images only start mattering past this length.
        if word_count < 600 or not sections:
            return SEOCheck(
                check_id="section_images",
                status="pass",
                message=(
                    "Article is short enough that "
                    "in-body images aren't essential."
                ),
                weight=5,
            )

        total_sections = len(sections)
        illustrated_sections = sum(
            1
            for section in sections
            if section.image_urls
        )

        if illustrated_sections == 0:
            return SEOCheck(
                check_id="section_images",
                status="warning",
                message=(
                    f"{word_count}-word article has no "
                    "in-body images. Aim for roughly one "
                    "image every 300-500 words — assign "
                    "images to sections from the Library "
                    "editor."
                ),
                weight=5,
            )

        coverage = (
            illustrated_sections / total_sections
        )

        if coverage < 0.25:
            return SEOCheck(
                check_id="section_images",
                status="warning",
                message=(
                    f"Only {illustrated_sections} of "
                    f"{total_sections} sections have an "
                    "image — consider adding a few more "
                    f"for a {word_count}-word article."
                ),
                weight=5,
            )

        return SEOCheck(
            check_id="section_images",
            status="pass",
            message=(
                f"{illustrated_sections} of "
                f"{total_sections} sections have an "
                "image."
            ),
            weight=5,
        )

    def _check_structured_data(
        self,
        schema_type: SchemaType,
        json_ld: dict,
    ) -> SEOCheck:
        if (
            schema_type
            not in {
                "Article",
                "BlogPosting",
                "NewsArticle",
            }
        ):
            return SEOCheck(
                check_id="structured_data",
                status="fail",
                message=(
                    "Unsupported article schema "
                    "type."
                ),
                weight=10,
            )

        if not json_ld.get(
            "headline"
        ):
            return SEOCheck(
                check_id="structured_data",
                status="fail",
                message=(
                    "Structured data headline "
                    "is missing."
                ),
                weight=10,
            )

        return SEOCheck(
            check_id="structured_data",
            status="pass",
            message=(
                f"{schema_type} structured "
                f"data has been generated."
            ),
            weight=10,
        )

    def _check_citations(
        self,
        request: SEORequest,
    ) -> SEOCheck:
        citation_count = sum(
            len(
                section.citation_ids
            )
            for section
            in request.article.sections
        )

        citation_count += len(
            request
            .article
            .introduction
            .citation_ids
        )

        if (
            request.article.sources
            and citation_count == 0
        ):
            return SEOCheck(
                check_id="citations",
                status="warning",
                message=(
                    "Research sources exist but "
                    "the article contains no "
                    "source citations."
                ),
                weight=5,
            )

        return SEOCheck(
            check_id="citations",
            status="pass",
            message=(
                "Article source references are "
                "available where used."
            ),
            weight=5,
        )

    def _check_word_count(
        self,
        request: SEORequest,
    ) -> SEOCheck:
        actual = (
            request.article.total_word_count
        )
        target = (
            request.brief.target_word_count
        )

        if target <= 0:
            return SEOCheck(
                check_id="word_count",
                status="pass",
                message=(
                    "No target word count was "
                    "set for this article."
                ),
                weight=5,
            )

        deviation = (
            abs(actual - target) / target
        )

        if deviation <= 0.15:
            return SEOCheck(
                check_id="word_count",
                status="pass",
                message=(
                    f"Article is {actual} words, "
                    f"close to the {target}-word "
                    "target."
                ),
                weight=5,
            )

        if deviation <= 0.35:
            return SEOCheck(
                check_id="word_count",
                status="warning",
                message=(
                    f"Article is {actual} words "
                    f"against a {target}-word "
                    "target — noticeably off the "
                    "brief."
                ),
                weight=5,
            )

        return SEOCheck(
            check_id="word_count",
            status="fail",
            message=(
                f"Article is {actual} words "
                f"against a {target}-word "
                "target — far outside the brief."
            ),
            weight=5,
        )

    def _calculate_readiness_score(
        self,
        checks: list[SEOCheck],
    ) -> int:
        total_weight = sum(
            check.weight
            for check in checks
        )

        earned = 0.0

        for check in checks:
            if check.status == "pass":
                earned += check.weight
            elif check.status == "warning":
                earned += (
                    check.weight * 0.5
                )

        if total_weight == 0:
            return 0

        return round(
            earned
            / total_weight
            * 100
        )


seo_service = SEOService()
