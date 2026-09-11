from app.schemas.research import (
    ResearchFact,
    ResearchResult,
    ResearchSource,
)
from app.services.research_merge import (
    merge_research_results,
)


def make_research(
    *,
    summary: str,
    source_url: str,
    entity: str,
) -> ResearchResult:
    return ResearchResult(
        topic="Testing pytest",
        search_intent="informational",
        summary=summary,
        queries_used=[f"query about {entity}"],
        questions_to_answer=["What is it?"],
        key_facts=[
            ResearchFact(
                claim=f"{entity} is real.",
                source_urls=[source_url],
            )
        ],
        statistics=[],
        recent_developments=[],
        important_entities=[entity],
        controversies_or_uncertainties=[],
        content_gaps=[],
        article_angles=[],
        sources=[
            ResearchSource(
                title=entity,
                url=source_url,
                domain="example.com",
            )
        ],
    )


def test_merge_keeps_primary_sources_first() -> None:
    primary = make_research(
        summary="Document summary.",
        source_url="doc://abc/chunk/0",
        entity="DocEntity",
    )
    secondary = make_research(
        summary="Web summary.",
        source_url="https://example.com/page",
        entity="WebEntity",
    )

    merged = merge_research_results(primary, secondary)

    assert [
        source.url for source in merged.sources
    ] == [
        "doc://abc/chunk/0",
        "https://example.com/page",
    ]


def test_merge_combines_facts_and_dedupes_entities() -> None:
    primary = make_research(
        summary="Document summary.",
        source_url="doc://abc/chunk/0",
        entity="Shared Entity",
    )
    secondary = make_research(
        summary="Web summary.",
        source_url="https://example.com/page",
        entity="Shared Entity",
    )

    merged = merge_research_results(primary, secondary)

    assert len(merged.key_facts) == 2
    assert merged.important_entities == ["Shared Entity"]
    assert "Document summary." in merged.summary
    assert "Web summary." in merged.summary


def test_merge_deduplicates_sources_by_url() -> None:
    primary = make_research(
        summary="A",
        source_url="doc://abc/chunk/0",
        entity="X",
    )
    secondary = make_research(
        summary="B",
        source_url="doc://abc/chunk/0",
        entity="Y",
    )

    merged = merge_research_results(primary, secondary)

    assert len(merged.sources) == 1
