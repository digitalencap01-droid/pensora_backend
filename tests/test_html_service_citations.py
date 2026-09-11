from app.services.html_service import HTMLService


def build_service() -> HTMLService:
    return HTMLService()


def test_build_source_catalog_numbers_sources_in_order():
    service = build_service()

    catalog = service._build_source_catalog(
        [
            _source("S1", "https://a.example.com", "A"),
            _source("S2", "https://b.example.com", "B"),
        ]
    )

    assert catalog["S1"]["number"] == 1
    assert catalog["S2"]["number"] == 2


def test_build_source_catalog_drops_unsafe_urls():
    service = build_service()

    catalog = service._build_source_catalog(
        [
            _source(
                "S1",
                "javascript:alert(1)",
                "Bad",
            ),
            _source(
                "S2",
                "https://example.com/page",
                "Good",
            ),
        ]
    )

    assert "S1" not in catalog
    assert "S2" in catalog


def test_build_source_catalog_keeps_document_sources_as_non_links():
    service = build_service()

    catalog = service._build_source_catalog(
        [
            _source(
                "S1",
                "doc://11111111-1111-1111-1111-111111111111"
                "/chunk/0",
                "report.pdf — part 1",
            ),
        ]
    )

    assert "S1" in catalog
    assert catalog["S1"]["is_link"] is False


def test_replace_citations_strips_known_markers():
    service = build_service()
    catalog = {
        "S1": {
            "number": 1,
            "title": "A",
            "url": "https://a.example.com",
            "domain": "a.example.com",
        }
    }

    result = service._replace_citations(
        "Some fact [S1] and more text.",
        catalog,
    )

    assert "[S1]" not in result
    assert "Some fact" in result


def test_replace_citations_strips_markers_outside_the_section_evidence():
    """The trust boundary this app is built around: a model can't
    smuggle a citation to a source it wasn't given for this section.
    """
    service = build_service()
    # S1 is a real source overall, but not part of *this* section's
    # catalog — simulating a model citing outside its scoped evidence.
    catalog: dict = {}

    result = service._replace_citations(
        "An invented claim [S1] here.",
        catalog,
    )

    assert "[S1]" not in result


def test_replace_citations_handles_multi_digit_ids():
    service = build_service()
    catalog = {
        "S13": {
            "number": 13,
            "title": "Thirteenth source",
            "url": "https://example.com/13",
            "domain": "example.com",
        }
    }

    result = service._replace_citations(
        "A fact cited from [S13].",
        catalog,
    )

    assert "[S13]" not in result
    assert "A fact cited from" in result


def test_render_markdown_produces_no_visible_citation_markers():
    service = build_service()
    catalog = {
        "S1": {
            "number": 1,
            "title": "A",
            "url": "https://a.example.com",
            "domain": "a.example.com",
        },
        "S2": {
            "number": 2,
            "title": "B",
            "url": "https://b.example.com",
            "domain": "b.example.com",
        },
    }

    html = service._render_markdown(
        "Revenue grew 40% [S1] year over year [S2].",
        catalog,
    )

    assert "[S1]" not in html
    assert "[S2]" not in html
    assert "Revenue grew 40%" in html


def _source(source_id: str, url: str, title: str):
    from urllib.parse import urlparse

    from app.schemas.article import ArticleSource

    return ArticleSource(
        source_id=source_id,
        title=title,
        url=url,
        domain=urlparse(url).netloc or url,
    )
