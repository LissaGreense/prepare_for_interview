"""Shared offline fakes for the scoping graph (not collected as tests)."""

from app.generation.scoping import FetchedDoc, TopicNode


def fake_expand(query: str, parent_id: str | None) -> list[TopicNode]:
    """Deterministic stand-in for search + LLM expansion."""
    if parent_id is None:
        return [
            {"id": "rest", "label": "REST API", "kind": "subtopic", "parent_id": None},
            {
                "id": "graphql",
                "label": "GraphQL",
                "kind": "subtopic",
                "parent_id": None,
            },
            {"id": "react", "label": "React", "kind": "technology", "parent_id": None},
        ]
    if parent_id == "react":
        return [
            {
                "id": "react/hooks",
                "label": "Hooks",
                "kind": "subtopic",
                "parent_id": "react",
            },
            {
                "id": "react/jsx",
                "label": "JSX",
                "kind": "subtopic",
                "parent_id": "react",
            },
            {
                "id": "react/context",
                "label": "Context",
                "kind": "subtopic",
                "parent_id": "react",
            },
        ]
    return [
        {
            "id": f"{parent_id}/basics",
            "label": f"{query} basics",
            "kind": "subtopic",
            "parent_id": parent_id,
        },
        {
            "id": f"{parent_id}/advanced",
            "label": f"{query} advanced",
            "kind": "subtopic",
            "parent_id": parent_id,
        },
    ]


def fake_fetch(topic_id: str, label: str) -> FetchedDoc:
    """Stand-in for search + WebBaseLoader doc fetch."""
    return {
        "topic_id": topic_id,
        "text": f"docs for {label}",
        "sources": [f"https://example.test/{topic_id}"],
    }
