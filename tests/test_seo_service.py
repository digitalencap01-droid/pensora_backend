from datetime import datetime, timedelta, timezone

from app.schemas.article import (
    ArticleBlock,
    ArticleResult,
    ArticleSection,
)
from app.schemas.content_brief import (
    ContentBriefResult,
)
from app.schemas.seo import SEORequest
from app.services.seo_service import (
    SEOService,
)


def make_section(
    section_id: str,
    image_url: str | None = None,
) -> ArticleSection:
    return ArticleSection(
        section_id=section_id,
        heading=f"Heading {section_id}",
        content_markdown="Body text.",
        citation_ids=[],
        summary="Summary.",
        word_count=200,
        image_urls=[image_url] if image_url else [],
        image_alts=["Alt text"] if image_url else [],
    )


def make_article(
    total_word_count: int = 1000,
    sections: list[ArticleSection] | None = None,
) -> ArticleResult:
    return ArticleResult(
        topic="Testing pytest",
        title="A Guide to Testing pytest",
        h1="A Guide to Testing pytest",
        language="English",
        introduction=ArticleBlock(
            content_markdown="Intro [S1]",
            citation_ids=["S1"],
            word_count=50,
        ),
        sections=sections or [],
        conclusion=ArticleBlock(
            content_markdown="Conclusion",
            citation_ids=[],
            word_count=50,
        ),
        sources=[],
        total_word_count=total_word_count,
        article_markdown="# Title\n\nBody",
    )


def make_brief(
    target_word_count: int = 1000,
) -> ContentBriefResult:
    return ContentBriefResult(
        topic="Testing pytest",
        article_type="blog",
        tone="professional",
        target_word_count=target_word_count,
        primary_keyword="pytest testing",
        search_intent="informational",
        content_angle="angle",
        unique_value_proposition="uvp",
        target_reader="developers",
        reader_problem="problem",
        reader_outcome="outcome",
        recommended_title="A Guide to Testing pytest",
        alternative_titles=[],
        h1="A Guide to Testing pytest",
        introduction_strategy="strategy",
        sections=[],
        conclusion_strategy="strategy",
        cta_strategy=None,
        image_opportunities=[],
        internal_link_opportunities=[],
        important_warnings=[],
    )


def make_request(**overrides) -> SEORequest:
    defaults = dict(
        article=make_article(),
        brief=make_brief(),
        site_name="Test Site",
        site_url="https://example.com",
        date_published=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return SEORequest(**defaults)


def build_service() -> SEOService:
    return SEOService()


def test_word_count_passes_within_15_percent():
    service = build_service()
    request = make_request(
        article=make_article(total_word_count=1080),
        brief=make_brief(target_word_count=1000),
    )

    check = service._check_word_count(request)

    assert check.status == "pass"


def test_word_count_warns_between_15_and_35_percent():
    service = build_service()
    request = make_request(
        article=make_article(total_word_count=1300),
        brief=make_brief(target_word_count=1000),
    )

    check = service._check_word_count(request)

    assert check.status == "warning"


def test_word_count_fails_beyond_35_percent():
    service = build_service()
    request = make_request(
        article=make_article(total_word_count=500),
        brief=make_brief(target_word_count=1000),
    )

    check = service._check_word_count(request)

    assert check.status == "fail"


def test_dates_pass_when_published_is_set():
    service = build_service()
    request = make_request(
        date_published=datetime.now(timezone.utc)
    )

    check = service._check_dates(request)

    assert check.status == "pass"


def test_dates_warn_when_published_is_missing():
    service = build_service()
    request = make_request(date_published=None)

    check = service._check_dates(request)

    assert check.status == "warning"


def test_dates_fail_when_modified_before_published():
    service = build_service()
    now = datetime.now(timezone.utc)
    request = make_request(
        date_published=now,
        date_modified=now - timedelta(days=1),
    )

    check = service._check_dates(request)

    assert check.status == "fail"


def test_images_warn_when_none_provided():
    service = build_service()

    check = service._check_images([])

    assert check.status == "warning"


def test_images_pass_when_provided():
    service = build_service()

    check = service._check_images(
        ["https://example.com/cover.jpg"]
    )

    assert check.status == "pass"


def test_readiness_score_is_100_when_everything_passes():
    service = build_service()
    checks = [
        service._check_dates(
            make_request(
                date_published=datetime.now(timezone.utc)
            )
        ),
        service._check_images(
            ["https://example.com/cover.jpg"]
        ),
    ]

    score = service._calculate_readiness_score(
        checks
    )

    assert score == 100


def test_readiness_score_reflects_partial_credit_for_warnings():
    service = build_service()
    # One check worth 10 that fully passes, one worth 10 that only
    # half-credits as a warning -> (10 + 5) / 20 * 100 == 75.
    checks = [
        service._check_images(
            ["https://example.com/cover.jpg"]
        ),
        service._check_dates(
            make_request(date_published=None)
        ),
    ]

    score = service._calculate_readiness_score(
        checks
    )

    assert score == 75


def test_section_images_pass_for_short_articles_with_no_images():
    service = build_service()
    request = make_request(
        article=make_article(
            total_word_count=400,
            sections=[make_section("s1")],
        )
    )

    check = service._check_section_images(request)

    assert check.status == "pass"


def test_section_images_warn_when_long_article_has_none():
    service = build_service()
    request = make_request(
        article=make_article(
            total_word_count=1500,
            sections=[
                make_section("s1"),
                make_section("s2"),
                make_section("s3"),
            ],
        )
    )

    check = service._check_section_images(request)

    assert check.status == "warning"


def test_section_images_warn_on_low_coverage():
    service = build_service()
    request = make_request(
        article=make_article(
            total_word_count=1500,
            sections=[
                make_section(
                    "s1", image_url="https://x/1.png"
                ),
                make_section("s2"),
                make_section("s3"),
                make_section("s4"),
                make_section("s5"),
            ],
        )
    )

    check = service._check_section_images(request)

    assert check.status == "warning"


def test_section_images_pass_with_good_coverage():
    service = build_service()
    request = make_request(
        article=make_article(
            total_word_count=1500,
            sections=[
                make_section(
                    "s1", image_url="https://x/1.png"
                ),
                make_section(
                    "s2", image_url="https://x/2.png"
                ),
                make_section("s3"),
            ],
        )
    )

    check = service._check_section_images(request)

    assert check.status == "pass"
