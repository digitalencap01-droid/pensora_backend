from app.schemas.article import (
    ArticleBlock,
    ArticleResult,
    ArticleSection,
    ArticleSource,
)
from app.services.image_placement import (
    assign_images_from_citations,
    distribute_images_across_sections,
)


def make_section(
    section_id: str,
    word_count: int,
    image_urls: list[str] | None = None,
    citation_ids: list[str] | None = None,
) -> ArticleSection:
    return ArticleSection(
        section_id=section_id,
        heading=f"Heading {section_id}",
        content_markdown="Body text.",
        citation_ids=citation_ids or [],
        summary="Summary.",
        word_count=word_count,
        image_urls=image_urls or [],
        image_alts=(
            ["Alt"] * len(image_urls) if image_urls else []
        ),
    )


def make_article(
    sections: list[ArticleSection],
    sources: list[ArticleSource] | None = None,
) -> ArticleResult:
    return ArticleResult(
        topic="Testing pytest",
        title="A Guide to Testing pytest",
        h1="A Guide to Testing pytest",
        language="English",
        introduction=ArticleBlock(
            content_markdown="Intro",
            citation_ids=[],
            word_count=50,
        ),
        sections=sections,
        conclusion=ArticleBlock(
            content_markdown="Conclusion",
            citation_ids=[],
            word_count=50,
        ),
        sources=sources or [],
        total_word_count=sum(
            s.word_count for s in sections
        ),
        article_markdown="# Title\n\nBody",
    )


def test_no_images_leaves_article_unchanged():
    article = make_article(
        [make_section("s1", 400)]
    )

    result = distribute_images_across_sections(
        article, []
    )

    assert result is article


def test_no_sections_leaves_article_unchanged():
    article = make_article([])

    result = distribute_images_across_sections(
        article, ["https://x/1.png"]
    )

    assert result is article


def test_images_spaced_roughly_every_350_words():
    article = make_article(
        [
            make_section("s1", 200),
            make_section("s2", 200),
            make_section("s3", 200),
            make_section("s4", 200),
            make_section("s5", 200),
            make_section("s6", 200),
        ]
    )

    result = distribute_images_across_sections(
        article,
        ["https://x/1.png", "https://x/2.png"],
        words_per_image=350,
    )

    placements = [
        section.image_urls
        for section in result.sections
    ]

    assert placements == [
        [],
        ["https://x/1.png"],
        [],
        ["https://x/2.png"],
        [],
        [],
    ]


def test_does_not_overwrite_an_already_illustrated_section():
    article = make_article(
        [
            make_section(
                "s1", 400, image_urls=["https://x/existing.png"]
            ),
            make_section("s2", 400),
        ]
    )

    result = distribute_images_across_sections(
        article, ["https://x/new.png"]
    )

    assert result.sections[0].image_urls == [
        "https://x/existing.png"
    ]
    assert result.sections[1].image_urls == [
        "https://x/new.png"
    ]


def test_runs_out_of_images_gracefully():
    article = make_article(
        [
            make_section("s1", 400),
            make_section("s2", 400),
            make_section("s3", 400),
        ]
    )

    result = distribute_images_across_sections(
        article, ["https://x/only.png"]
    )

    placements = [
        section.image_urls
        for section in result.sections
    ]

    assert placements == [
        ["https://x/only.png"],
        [],
        [],
    ]


def test_assign_images_from_citations_uses_cited_source_urls():
    sources = [
        ArticleSource(
            source_id="S1",
            title="Image 1",
            url="https://x/1.png",
            domain="uploaded-images",
        ),
        ArticleSource(
            source_id="S2",
            title="Image 2",
            url="https://x/2.png",
            domain="uploaded-images",
        ),
    ]
    article = make_article(
        [
            make_section(
                "s1", 300, citation_ids=["S1"]
            ),
            make_section(
                "s2", 300, citation_ids=["S2"]
            ),
            make_section("s3", 300),
        ],
        sources=sources,
    )

    result = assign_images_from_citations(article)

    assert result.sections[0].image_urls == [
        "https://x/1.png"
    ]
    assert result.sections[1].image_urls == [
        "https://x/2.png"
    ]
    assert result.sections[2].image_urls == []


def test_assign_images_from_citations_skips_illustrated_sections():
    sources = [
        ArticleSource(
            source_id="S1",
            title="Image 1",
            url="https://x/1.png",
            domain="uploaded-images",
        ),
    ]
    article = make_article(
        [
            make_section(
                "s1",
                300,
                image_urls=["https://x/manual.png"],
                citation_ids=["S1"],
            ),
        ],
        sources=sources,
    )

    result = assign_images_from_citations(article)

    assert result.sections[0].image_urls == [
        "https://x/manual.png"
    ]


def test_assign_images_from_citations_no_op_without_sources():
    article = make_article(
        [make_section("s1", 300, citation_ids=["S1"])]
    )

    result = assign_images_from_citations(article)

    assert result is article


def test_assign_images_from_citations_respects_allowed_urls():
    sources = [
        ArticleSource(
            source_id="S1",
            title="Image 1",
            url="https://x/1.png",
            domain="uploaded-images",
        ),
        ArticleSource(
            source_id="S2",
            title="Image 2",
            url="https://x/2.png",
            domain="uploaded-images",
        ),
    ]
    article = make_article(
        [
            make_section(
                "s1", 300, citation_ids=["S1"]
            ),
            make_section(
                "s2", 300, citation_ids=["S2"]
            ),
        ],
        sources=sources,
    )

    result = assign_images_from_citations(
        article,
        allowed_urls={"https://x/1.png"},
    )

    assert result.sections[0].image_urls == [
        "https://x/1.png"
    ]
    # Cited, but not in allowed_urls (not user-selected) — must
    # not appear in the output.
    assert result.sections[1].image_urls == []
