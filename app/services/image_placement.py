from app.schemas.article import ArticleResult


DEFAULT_WORDS_PER_IMAGE = 350


def distribute_images_across_sections(
    article: ArticleResult,
    image_urls: list[str],
    words_per_image: int = DEFAULT_WORDS_PER_IMAGE,
) -> ArticleResult:
    """Spaces a pool of images through the article body roughly
    every `words_per_image` words, one per section, in reading
    order — instead of every selected image collapsing onto a
    single header image.
    """
    if not image_urls or not article.sections:
        return article

    image_queue = list(image_urls)
    cumulative_words = 0
    updated_sections = []

    for section in article.sections:
        cumulative_words += section.word_count

        section_image_urls = list(section.image_urls)
        section_image_alts = list(section.image_alts)

        if (
            image_queue
            and not section_image_urls
            and cumulative_words >= words_per_image
        ):
            next_image = image_queue.pop(0)
            section_image_urls.append(next_image)
            section_image_alts.append(section.heading)
            cumulative_words = 0

        updated_sections.append(
            section.model_copy(
                update={
                    "image_urls": section_image_urls,
                    "image_alts": section_image_alts,
                }
            )
        )

    return article.model_copy(
        update={"sections": updated_sections}
    )


def assign_images_from_citations(
    article: ArticleResult,
    allowed_urls: set[str] | None = None,
) -> ArticleResult:
    """For image-grounded articles, every research "source" the
    model can cite IS an uploaded image. Whichever images a section
    actually cited are the most semantically accurate ones to show
    there — more precise than blind word-count spacing. Only call
    this for image-batch-grounded generation; for web/document
    research, a cited source is not necessarily a real image.

    `allowed_urls`, when given, restricts placement to only those
    URLs (e.g. the images the user explicitly picked) — an uploaded
    image the model cited for its text but the user never selected
    should inform the writing, not appear in the output.
    """
    source_url_by_id = {
        source.source_id: source.url
        for source in article.sources
    }

    if not source_url_by_id:
        return article

    updated_sections = []

    for section in article.sections:
        if section.image_urls:
            updated_sections.append(section)
            continue

        cited_image_urls = [
            source_url_by_id[citation_id]
            for citation_id in section.citation_ids
            if citation_id in source_url_by_id
            and (
                allowed_urls is None
                or source_url_by_id[citation_id]
                in allowed_urls
            )
        ]

        if not cited_image_urls:
            updated_sections.append(section)
            continue

        updated_sections.append(
            section.model_copy(
                update={
                    "image_urls": cited_image_urls,
                    "image_alts": [
                        section.heading
                        for _ in cited_image_urls
                    ],
                }
            )
        )

    return article.model_copy(
        update={"sections": updated_sections}
    )
