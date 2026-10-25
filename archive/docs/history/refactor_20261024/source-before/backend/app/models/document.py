"""Identifiers shared by fixture and upload ingestion; fixture rules stay strict."""
import re
from uuid import UUID


def valid_document_id(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if re.fullmatch(r'D[0-9]{3}', value):
        return True
    try:
        parsed = UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except ValueError:
        return False
