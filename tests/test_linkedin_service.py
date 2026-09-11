import os

os.environ["DEBUG"] = "true"

from app.services.linkedin_service import LinkedInService


def test_sanitize_generated_text_removes_markdown_and_links() -> None:
    service = LinkedInService()

    raw = """
Reducing latency in OpenAI API calls is crucial.

**1. Choose the Right Model:**
Selecting the smallest model that fits your needs is often enough.
(https://lnkd.in/desQyJHh)

- **2. Minimize Token Usage:** Keep prompts concise.
[OpenAI](https://openai.com/) suggests streaming for better responsiveness.
"""

    assert service._sanitize_generated_text(raw) == (
        "Reducing latency in OpenAI API calls is crucial.\n\n"
        "Choose the Right Model:\n"
        "Selecting the smallest model that fits your needs is often enough.\n\n"
        "Minimize Token Usage: Keep prompts concise.\n"
        "OpenAI suggests streaming for better responsiveness."
    )


def test_sanitize_generated_text_removes_inline_domains() -> None:
    service = LinkedInService()

    raw = """
RAG combines the generative capabilities of LLMs with real-time access to an organization's proprietary information. mckinsey.com

Key Benefits of Implementing RAG:

Enhanced Accuracy and Relevance: By accessing up-to-date, enterprise-specific data, RAG ensures that AI-generated responses are precise and tailored. affixed.ai
"""

    assert service._sanitize_generated_text(raw) == (
        "RAG combines the generative capabilities of LLMs with real-time "
        "access to an organization's proprietary information.\n\n"
        "Key Benefits of Implementing RAG:\n\n"
        "Enhanced Accuracy and Relevance: By accessing up-to-date, "
        "enterprise-specific data, RAG ensures that AI-generated responses "
        "are precise and tailored."
    )


def test_sanitize_for_linkedin_commentary_removes_brackets() -> None:
    service = LinkedInService()

    raw = (
        "One such innovation is Retrieval-Augmented Generation (RAG), "
        "which uses [private] data sources."
    )

    assert service._sanitize_for_linkedin_commentary(raw) == (
        "One such innovation is Retrieval-Augmented Generation RAG, "
        "which uses private data sources."
    )
