from pydantic import BaseModel, Field


class XhsAuthorPageNoteItem(BaseModel):
    note_id: str = Field(..., validation_alias="noteId", description="Note id")
    note_title: str = Field(..., validation_alias="displayTitle")


class XhsAuthorPageNote(BaseModel):
    id: str = Field(..., description="Note id, equal to note_card.note_id")
    note_item: XhsAuthorPageNoteItem = Field(..., validation_alias="noteCard")
