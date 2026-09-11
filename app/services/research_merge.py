from app.schemas.research import ResearchResult, ResearchSource


def merge_research_results(
    primary: ResearchResult,
    secondary: ResearchResult,
) -> ResearchResult:
    """Combine two research results into one, e.g. document-grounded
    research plus supplementary live web research. `primary`'s sources
    are kept first, so citation ids (S1, S2, ...) are assigned to it
    first downstream in the article service.
    """
    return primary.model_copy(
        update={
            "summary": (
                f"{primary.summary}\n\n{secondary.summary}"
            ),
            "queries_used": (
                primary.queries_used
                + secondary.queries_used
            ),
            "questions_to_answer": _merge_strings(
                primary.questions_to_answer,
                secondary.questions_to_answer,
            ),
            "key_facts": (
                primary.key_facts + secondary.key_facts
            ),
            "statistics": (
                primary.statistics + secondary.statistics
            ),
            "recent_developments": (
                primary.recent_developments
                + secondary.recent_developments
            ),
            "important_entities": _merge_strings(
                primary.important_entities,
                secondary.important_entities,
            ),
            "controversies_or_uncertainties": (
                _merge_strings(
                    primary.controversies_or_uncertainties,
                    secondary.controversies_or_uncertainties,
                )
            ),
            "content_gaps": _merge_strings(
                primary.content_gaps,
                secondary.content_gaps,
            ),
            "article_angles": _merge_strings(
                primary.article_angles,
                secondary.article_angles,
            ),
            "sources": _merge_sources(
                primary.sources,
                secondary.sources,
            ),
        }
    )


def _merge_sources(
    first: list[ResearchSource],
    second: list[ResearchSource],
) -> list[ResearchSource]:
    merged: dict[str, ResearchSource] = {
        source.url: source for source in first
    }

    for source in second:
        merged.setdefault(source.url, source)

    return list(merged.values())


def _merge_strings(
    first: list[str],
    second: list[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in first + second:
        normalized = value.strip().casefold()

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        result.append(value.strip())

    return result
