from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import frontmatter

TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]")


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    source_id: str
    title: str
    keywords: tuple[str, ...]
    answer: str


@dataclass(frozen=True, slots=True)
class KnowledgeMatch:
    source_id: str
    title: str
    answer: str
    score: float


class MarkdownKnowledgeBase:
    def __init__(self, documents: tuple[KnowledgeDocument, ...], minimum_score: float = 0.35):
        if not documents:
            raise ValueError("Knowledge base must contain at least one document")
        self.documents = documents
        self.minimum_score = minimum_score

    @classmethod
    def from_directory(cls, directory: str | Path) -> MarkdownKnowledgeBase:
        root = Path(directory)
        documents: list[KnowledgeDocument] = []
        for path in sorted(root.glob("*.md")):
            post = frontmatter.load(path)
            source_id = str(post.get("id", "")).strip()
            title = str(post.get("title", "")).strip()
            keywords = post.get("keywords")
            answer = post.content.strip()
            if not source_id or not title or not answer:
                raise ValueError(f"Knowledge file {path.name} is missing required metadata")
            if not isinstance(keywords, list) or not all(
                isinstance(item, str) for item in keywords
            ):
                raise ValueError(f"Knowledge file {path.name} keywords must be a string list")
            documents.append(
                KnowledgeDocument(
                    source_id=source_id,
                    title=title,
                    keywords=tuple(item.strip() for item in keywords if item.strip()),
                    answer=answer,
                )
            )
        return cls(tuple(documents))

    def search(self, query: str) -> KnowledgeMatch | None:
        query_tokens = _tokens(query)
        if not query_tokens:
            return None
        ranked = sorted(
            ((_score(query_tokens, document), document) for document in self.documents),
            key=lambda item: (-item[0], item[1].source_id),
        )
        score, document = ranked[0]
        if score < self.minimum_score:
            return None
        return KnowledgeMatch(
            source_id=document.source_id,
            title=document.title,
            answer=document.answer,
            score=round(score, 3),
        )


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return set(TOKEN_PATTERN.findall(normalized))


def _score(query_tokens: set[str], document: KnowledgeDocument) -> float:
    keyword_groups = tuple(_tokens(keyword) for keyword in document.keywords)
    keyword_tokens = set().union(*keyword_groups)
    title_tokens = _tokens(document.title)
    searchable = keyword_tokens | title_tokens
    if not searchable:
        return 0.0
    overlap = query_tokens & searchable
    if not overlap:
        return 0.0
    if any(group and group <= query_tokens for group in keyword_groups):
        return min(1.0, 0.75 + (len(overlap) * 0.03))
    precision = len(overlap) / len(query_tokens)
    coverage = len(overlap) / len(searchable)
    return min(1.0, (precision * 0.8) + (coverage * 0.2))
