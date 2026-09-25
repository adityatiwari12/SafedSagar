from pydantic import BaseModel


class PriorArtResult(BaseModel):
    doc_id: str
    title: str
    authority: str
    jurisdiction: str
    doc_type: str
    section_or_article: str | None
    source_url: str
    snippet: str
