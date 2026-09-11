import json
import re

from app.prompts.article import (
    ARTICLE_CONCLUSION_PROMPT,
    ARTICLE_INTRODUCTION_PROMPT,
    ARTICLE_SECTION_PROMPT,
)
from app.schemas.article import (
    ArticleBlock,
    ArticleRequest,
    ArticleResult,
    ArticleSection,
    ArticleSource,
    GeneratedArticleBlockAI,
)
from app.schemas.content_brief import OutlineSection
from app.schemas.research import ResearchFact
from app.services.openai_service import openai_service


class ArticleService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def generate_article(
        self,
        request: ArticleRequest,
    ) -> ArticleResult:
        sources = self._build_source_catalog(
            request
        )

        url_to_source_id = {
            source.url: source.source_id
            for source in sources
        }

        generated_sections: list[
            ArticleSection
        ] = []

        section_summaries: list[dict] = []

        for section in request.brief.sections:
            generated_section = (
                await self._generate_section(
                    request=request,
                    section=section,
                    url_to_source_id=(
                        url_to_source_id
                    ),
                    previous_summaries=(
                        section_summaries
                    ),
                )
            )

            generated_sections.append(
                generated_section
            )

            section_summaries.append(
                {
                    "section_id": (
                        generated_section.section_id
                    ),
                    "heading": (
                        generated_section.heading
                    ),
                    "summary": (
                        generated_section.summary
                    ),
                }
            )

        conclusion = await self._generate_conclusion(
            request=request,
            section_summaries=section_summaries,
            allowed_source_ids={
                source.source_id
                for source in sources
            },
        )

        introduction = (
            await self._generate_introduction(
                request=request,
                section_summaries=section_summaries,
                sources=sources,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        used_source_ids = (
            self._collect_used_source_ids(
                introduction=introduction,
                sections=generated_sections,
                conclusion=conclusion,
            )
        )

        used_sources = [
            source
            for source in sources
            if source.source_id
            in used_source_ids
        ]

        total_word_count = (
            introduction.word_count
            + sum(
                section.word_count
                for section
                in generated_sections
            )
            + conclusion.word_count
        )

        article_markdown = (
            self._assemble_markdown(
                request=request,
                introduction=introduction,
                sections=generated_sections,
                conclusion=conclusion,
                sources=used_sources,
            )
        )

        return ArticleResult(
            topic=request.research.topic,
            title=(
                request.brief.recommended_title
            ),
            h1=request.brief.h1,
            language=request.language,
            introduction=introduction,
            sections=generated_sections,
            conclusion=conclusion,
            sources=used_sources,
            total_word_count=total_word_count,
            article_markdown=article_markdown,
        )

    async def regenerate_section(
        self,
        request: ArticleRequest,
        current_article: ArticleResult,
        section_id: str,
        instructions: str | None = None,
    ) -> ArticleResult:
        outline_section = next(
            (
                section
                for section
                in request.brief.sections
                if section.section_id
                == section_id
            ),
            None,
        )

        if outline_section is None:
            raise ValueError(
                f"Section '{section_id}' "
                f"does not exist in the brief."
            )

        current_index = next(
            (
                index
                for index, section
                in enumerate(
                    current_article.sections
                )
                if section.section_id
                == section_id
            ),
            None,
        )

        if current_index is None:
            raise ValueError(
                f"Section '{section_id}' "
                f"does not exist in the article."
            )

        sources = self._build_source_catalog(
            request
        )

        url_to_source_id = {
            source.url: source.source_id
            for source in sources
        }

        previous_summaries = [
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "summary": section.summary,
            }
            for section
            in current_article.sections[
                :current_index
            ]
        ]

        original_instructions = (
            request.additional_instructions
            or ""
        )

        regeneration_instruction = (
            instructions
            or ""
        )

        combined_instructions = (
            f"{original_instructions}\n\n"
            f"Section regeneration instructions:\n"
            f"{regeneration_instruction}"
        ).strip()

        regeneration_request = (
            request.model_copy(
                update={
                    "additional_instructions":
                        combined_instructions
                }
            )
        )

        regenerated_section = (
            await self._generate_section(
                request=regeneration_request,
                section=outline_section,
                url_to_source_id=(
                    url_to_source_id
                ),
                previous_summaries=(
                    previous_summaries
                ),
            )
        )

        # Regeneration only rewrites the content — an image
        # assigned to this section (from the Library editor) isn't
        # something the model touched, so keep it.
        existing_section = current_article.sections[
            current_index
        ]

        regenerated_section = (
            regenerated_section.model_copy(
                update={
                    "image_urls": (
                        existing_section.image_urls
                    ),
                    "image_alts": (
                        existing_section.image_alts
                    ),
                }
            )
        )

        updated_sections = list(
            current_article.sections
        )

        updated_sections[
            current_index
        ] = regenerated_section

        used_source_ids = (
            self._collect_used_source_ids(
                introduction=(
                    current_article.introduction
                ),
                sections=updated_sections,
                conclusion=(
                    current_article.conclusion
                ),
            )
        )

        used_sources = [
            source
            for source in sources
            if source.source_id
            in used_source_ids
        ]

        total_word_count = (
            current_article
            .introduction
            .word_count
            + sum(
                section.word_count
                for section
                in updated_sections
            )
            + current_article
            .conclusion
            .word_count
        )

        article_markdown = (
            self._assemble_markdown(
                request=request,
                introduction=(
                    current_article.introduction
                ),
                sections=updated_sections,
                conclusion=(
                    current_article.conclusion
                ),
                sources=used_sources,
            )
        )

        return current_article.model_copy(
            update={
                "sections":
                    updated_sections,
                "sources":
                    used_sources,
                "total_word_count":
                    total_word_count,
                "article_markdown":
                    article_markdown,
            }
        )

    def _build_source_catalog(
        self,
        request: ArticleRequest,
    ) -> list[ArticleSource]:
        sources: list[ArticleSource] = []

        for index, source in enumerate(
            request.research.sources,
            start=1,
        ):
            sources.append(
                ArticleSource(
                    source_id=f"S{index}",
                    title=source.title,
                    url=source.url,
                    domain=source.domain,
                )
            )

        return sources

    async def _generate_section(
        self,
        request: ArticleRequest,
        section: OutlineSection,
        url_to_source_id: dict[str, str],
        previous_summaries: list[dict],
    ) -> ArticleSection:
        evidence = (
            self._build_section_evidence(
                request=request,
                section=section,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        allowed_source_ids = {
            url_to_source_id[url]
            for url in section.evidence_urls
            if url in url_to_source_id
        }

        source_catalog = (
            self._source_catalog_for_ids(
                request=request,
                source_ids=allowed_source_ids,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        payload = {
            "article": {
                "topic": (
                    request.research.topic
                ),
                "title": (
                    request
                    .brief
                    .recommended_title
                ),
                "h1": request.brief.h1,
                "article_type": (
                    request.brief.article_type
                ),
                "tone": request.brief.tone,
                "language": request.language,
                "target_reader": (
                    request.brief.target_reader
                ),
                "reader_problem": (
                    request.brief.reader_problem
                ),
                "reader_outcome": (
                    request.brief.reader_outcome
                ),
                "content_angle": (
                    request.brief.content_angle
                ),
                "primary_keyword": (
                    request
                    .brief
                    .primary_keyword
                ),
            },
            "current_section": {
                "section_id": (
                    section.section_id
                ),
                "heading": section.heading,
                "purpose": section.purpose,
                "target_keywords": (
                    section.target_keywords
                ),
                "semantic_terms": (
                    section.semantic_terms
                ),
                "questions_answered": (
                    section.questions_answered
                ),
                "key_points": (
                    section.key_points
                ),
                "subsections": [
                    {
                        "heading": (
                            subsection.heading
                        ),
                        "purpose": (
                            subsection.purpose
                        ),
                        "key_points": (
                            subsection.key_points
                        ),
                        "questions_answered": (
                            subsection
                            .questions_answered
                        ),
                    }
                    for subsection
                    in section.subsections
                ],
                "target_word_count": (
                    section.target_word_count
                ),
            },
            "evidence": evidence,
            "approved_sources": (
                source_catalog
            ),
            "previous_section_summaries": (
                previous_summaries
            ),
            "additional_instructions": (
                request.additional_instructions
            ),
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=ARTICLE_SECTION_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=(
                GeneratedArticleBlockAI
            ),
            store=False,
        )

        generated = response.output_parsed

        if generated is None:
            raise ValueError(
                f"Failed to generate section: "
                f"{section.section_id}"
            )

        cleaned_content = (
            self._sanitize_citations(
                generated.content_markdown,
                allowed_source_ids,
            )
        )

        citation_ids = (
            self._extract_citation_ids(
                cleaned_content
            )
        )

        return ArticleSection(
            section_id=section.section_id,
            heading=section.heading,
            content_markdown=cleaned_content,
            citation_ids=citation_ids,
            summary=generated.summary.strip(),
            word_count=self._word_count(
                cleaned_content
            ),
        )

    def _build_section_evidence(
        self,
        request: ArticleRequest,
        section: OutlineSection,
        url_to_source_id: dict[str, str],
    ) -> list[dict]:
        section_urls = set(
            section.evidence_urls
        )

        evidence: list[dict] = []

        evidence.extend(
            self._facts_to_evidence(
                facts=request.research.key_facts,
                evidence_type="key_fact",
                allowed_urls=section_urls,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        evidence.extend(
            self._facts_to_evidence(
                facts=request.research.statistics,
                evidence_type="statistic",
                allowed_urls=section_urls,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        evidence.extend(
            self._facts_to_evidence(
                facts=(
                    request
                    .research
                    .recent_developments
                ),
                evidence_type=(
                    "recent_development"
                ),
                allowed_urls=section_urls,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        return evidence

    def _facts_to_evidence(
        self,
        facts: list[ResearchFact],
        evidence_type: str,
        allowed_urls: set[str],
        url_to_source_id: dict[str, str],
    ) -> list[dict]:
        result: list[dict] = []

        for fact in facts:
            matching_urls = [
                url
                for url in fact.source_urls
                if url in allowed_urls
                and url in url_to_source_id
            ]

            if not matching_urls:
                continue

            result.append(
                {
                    "type": evidence_type,
                    "claim": fact.claim,
                    "source_ids": [
                        url_to_source_id[url]
                        for url in matching_urls
                    ],
                }
            )

        return result

    def _source_catalog_for_ids(
        self,
        request: ArticleRequest,
        source_ids: set[str],
        url_to_source_id: dict[str, str],
    ) -> list[dict]:
        result: list[dict] = []

        for source in request.research.sources:
            source_id = (
                url_to_source_id.get(
                    source.url
                )
            )

            if source_id not in source_ids:
                continue

            result.append(
                {
                    "source_id": source_id,
                    "title": source.title,
                    "domain": source.domain,
                }
            )

        return result

    async def _generate_conclusion(
        self,
        request: ArticleRequest,
        section_summaries: list[dict],
        allowed_source_ids: set[str],
    ) -> ArticleBlock:
        payload = {
            "article": {
                "topic": (
                    request.research.topic
                ),
                "title": (
                    request
                    .brief
                    .recommended_title
                ),
                "target_reader": (
                    request.brief.target_reader
                ),
                "reader_outcome": (
                    request.brief.reader_outcome
                ),
                "content_angle": (
                    request.brief.content_angle
                ),
                "tone": request.brief.tone,
                "language": request.language,
            },
            "section_summaries": (
                section_summaries
            ),
            "conclusion_strategy": (
                request
                .brief
                .conclusion_strategy
            ),
            "cta_strategy": (
                request.brief.cta_strategy
            ),
            "important_warnings": (
                request
                .brief
                .important_warnings
            ),
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=ARTICLE_CONCLUSION_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=(
                GeneratedArticleBlockAI
            ),
            store=False,
        )

        generated = response.output_parsed

        if generated is None:
            raise ValueError(
                "Failed to generate conclusion."
            )

        content = self._sanitize_citations(
            generated.content_markdown,
            allowed_source_ids,
        )

        return ArticleBlock(
            content_markdown=content,
            citation_ids=(
                self._extract_citation_ids(
                    content
                )
            ),
            word_count=self._word_count(
                content
            ),
        )

    async def _generate_introduction(
        self,
        request: ArticleRequest,
        section_summaries: list[dict],
        sources: list[ArticleSource],
        url_to_source_id: dict[str, str],
    ) -> ArticleBlock:
        allowed_source_ids = {
            source.source_id
            for source in sources
        }

        evidence = (
            self._build_intro_evidence(
                request=request,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        payload = {
            "article": {
                "topic": (
                    request.research.topic
                ),
                "title": (
                    request
                    .brief
                    .recommended_title
                ),
                "h1": request.brief.h1,
                "primary_keyword": (
                    request
                    .brief
                    .primary_keyword
                ),
                "search_intent": (
                    request.brief.search_intent
                ),
                "target_reader": (
                    request.brief.target_reader
                ),
                "reader_problem": (
                    request.brief.reader_problem
                ),
                "reader_outcome": (
                    request.brief.reader_outcome
                ),
                "tone": request.brief.tone,
                "language": request.language,
            },
            "introduction_strategy": (
                request
                .brief
                .introduction_strategy
            ),
            "section_summaries": (
                section_summaries
            ),
            "evidence": evidence,
            "approved_sources": [
                {
                    "source_id": (
                        source.source_id
                    ),
                    "title": source.title,
                    "domain": source.domain,
                }
                for source in sources
            ],
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=(
                ARTICLE_INTRODUCTION_PROMPT
            ),
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=(
                GeneratedArticleBlockAI
            ),
            store=False,
        )

        generated = response.output_parsed

        if generated is None:
            raise ValueError(
                "Failed to generate introduction."
            )

        content = self._sanitize_citations(
            generated.content_markdown,
            allowed_source_ids,
        )

        return ArticleBlock(
            content_markdown=content,
            citation_ids=(
                self._extract_citation_ids(
                    content
                )
            ),
            word_count=self._word_count(
                content
            ),
        )

    def _build_intro_evidence(
        self,
        request: ArticleRequest,
        url_to_source_id: dict[str, str],
    ) -> list[dict]:
        all_urls = set(
            url_to_source_id.keys()
        )

        evidence: list[dict] = []

        evidence.extend(
            self._facts_to_evidence(
                facts=request.research.key_facts,
                evidence_type="key_fact",
                allowed_urls=all_urls,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        evidence.extend(
            self._facts_to_evidence(
                facts=request.research.statistics,
                evidence_type="statistic",
                allowed_urls=all_urls,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        evidence.extend(
            self._facts_to_evidence(
                facts=(
                    request
                    .research
                    .recent_developments
                ),
                evidence_type=(
                    "recent_development"
                ),
                allowed_urls=all_urls,
                url_to_source_id=(
                    url_to_source_id
                ),
            )
        )

        return evidence[:15]

    def _sanitize_citations(
        self,
        content: str,
        allowed_source_ids: set[str],
    ) -> str:
        pattern = re.compile(
            r"\[(S\d+)\]"
        )

        def replace(match):
            source_id = match.group(1)

            if source_id in allowed_source_ids:
                return match.group(0)

            return ""

        cleaned = pattern.sub(
            replace,
            content,
        )

        cleaned = re.sub(
            r"[ \t]+\n",
            "\n",
            cleaned,
        )

        return cleaned.strip()

    def _extract_citation_ids(
        self,
        content: str,
    ) -> list[str]:
        matches = re.findall(
            r"\[(S\d+)\]",
            content,
        )

        seen: set[str] = set()
        result: list[str] = []

        for source_id in matches:
            if source_id in seen:
                continue

            seen.add(source_id)
            result.append(source_id)

        return result

    def _word_count(
        self,
        content: str,
    ) -> int:
        cleaned = re.sub(
            r"\[(S\d+)\]",
            "",
            content,
        )

        cleaned = re.sub(
            r"[#*_>`~-]",
            " ",
            cleaned,
        )

        words = re.findall(
            r"\b[\w'-]+\b",
            cleaned,
            flags=re.UNICODE,
        )

        return len(words)

    def _collect_used_source_ids(
        self,
        introduction: ArticleBlock,
        sections: list[ArticleSection],
        conclusion: ArticleBlock,
    ) -> set[str]:
        used = set(
            introduction.citation_ids
        )

        for section in sections:
            used.update(
                section.citation_ids
            )

        used.update(
            conclusion.citation_ids
        )

        return used

    def _assemble_markdown(
        self,
        request: ArticleRequest,
        introduction: ArticleBlock,
        sections: list[ArticleSection],
        conclusion: ArticleBlock,
        sources: list[ArticleSource],
    ) -> str:
        parts: list[str] = []

        parts.append(
            f"# {request.brief.h1}"
        )

        parts.append(
            introduction.content_markdown
        )

        for section in sections:
            parts.append(
                f"## {section.heading}"
            )

            parts.append(
                section.content_markdown
            )

        parts.append(
            "## Conclusion"
        )

        parts.append(
            conclusion.content_markdown
        )

        if sources:
            parts.append(
                "## Sources"
            )

            for source in sources:
                title = (
                    source.title
                    or source.domain
                )

                parts.append(
                    f"- [{source.source_id}] "
                    f"[{title}]({source.url})"
                )

        return "\n\n".join(
            parts
        ).strip()


article_service = ArticleService()
