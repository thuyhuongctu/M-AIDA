"""
Notion API synchronisation layer for M-AIDA v7.1.1.

Pushes PI-locked study records to a Notion database and retrieves existing
entries.  The Notion database must be pre-configured with properties that match
the StudyDatabaseEntry schema; see the README for the required schema.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from models import StudyDatabaseEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Property helpers
# ---------------------------------------------------------------------------


def _text(value: str) -> dict:
    """Build a Notion rich-text property payload."""
    return {"rich_text": [{"text": {"content": str(value)}}]}


def _title(value: str) -> dict:
    """Build a Notion title property payload."""
    return {"title": [{"text": {"content": str(value)}}]}


def _number(value: float | int | None) -> dict:
    """Build a Notion number property payload."""
    return {"number": value}


def _select(value: str | None) -> dict:
    """Build a Notion select property payload."""
    if value is None:
        return {"select": None}
    return {"select": {"name": value}}


def _checkbox(value: bool) -> dict:
    """Build a Notion checkbox property payload."""
    return {"checkbox": value}


def _date(value: datetime | None) -> dict:
    """Build a Notion date property payload (ISO 8601)."""
    if value is None:
        return {"date": None}
    return {"date": {"start": value.isoformat()}}


def _entry_to_properties(entry: StudyDatabaseEntry) -> dict[str, Any]:
    """Convert a StudyDatabaseEntry into Notion database properties.

    The property names match the expected Notion database column names exactly.
    Any mismatch between these names and the actual Notion schema will raise an
    APIResponseError at sync time, making failures explicit.
    """
    return {
        "Paper Title": _title(entry.paper_title),
        "Authors": _text(entry.authors),
        "Year": _number(entry.year),
        "Country": _text(entry.country),
        "study_id": _text(entry.study_id),
        "sample_n": _number(entry.sample_n),
        "effect_r": _number(entry.effect_r),
        "effect_t": _number(entry.effect_t),
        "effect_beta": _number(entry.effect_beta),
        "effect_df": _number(entry.effect_df),
        "p_value": _number(entry.p_value),
        "ci_lower": _number(entry.ci_lower),
        "ci_upper": _number(entry.ci_upper),
        "doi_measure": _select(entry.doi_measure),
        "performance_measure": _select(entry.performance_measure),
        "icrv_regime": _select(entry.icrv_regime),
        "dpl_phase": _select(entry.dpl_phase),
        "cdai_score": _number(entry.cdai_score),
        "extraction_confidence": _number(entry.extraction_confidence),
        "requires_verification": _checkbox(entry.requires_verification),
        "pi_locked": _checkbox(entry.pi_locked),
        "pi_notes": _text(entry.pi_notes),
        "extracted_at": _date(entry.extracted_at),
        "locked_at": _date(entry.locked_at),
    }


def _extract_text(prop: dict) -> str:
    """Pull plain text from a Notion rich-text or title property."""
    items: list[dict] = prop.get("rich_text") or prop.get("title") or []
    return "".join(item.get("plain_text", "") for item in items)


def _properties_to_entry(
    page_id: str, props: dict[str, Any]
) -> StudyDatabaseEntry:
    """Convert Notion page properties back to a StudyDatabaseEntry.

    Raises KeyError if required properties are missing from the Notion schema.
    """

    def _num(key: str) -> float | None:
        val = props.get(key, {}).get("number")
        return val

    def _int_num(key: str) -> int | None:
        val = _num(key)
        return int(val) if val is not None else None

    def _sel(key: str) -> str | None:
        sel = props.get(key, {}).get("select")
        return sel.get("name") if sel else None

    def _bool(key: str) -> bool:
        return bool(props.get(key, {}).get("checkbox", False))

    def _dt(key: str) -> datetime | None:
        date_prop = props.get(key, {}).get("date")
        if date_prop and date_prop.get("start"):
            return datetime.fromisoformat(date_prop["start"])
        return None

    return StudyDatabaseEntry(
        study_id=_extract_text(props.get("study_id", {})),
        paper_title=_extract_text(props.get("Paper Title", {})),
        authors=_extract_text(props.get("Authors", {})),
        year=int(_num("Year") or 0),
        country=_extract_text(props.get("Country", {})),
        sample_n=_int_num("sample_n"),
        effect_r=_num("effect_r"),
        effect_t=_num("effect_t"),
        effect_beta=_num("effect_beta"),
        effect_df=_int_num("effect_df"),
        p_value=_num("p_value"),
        ci_lower=_num("ci_lower"),
        ci_upper=_num("ci_upper"),
        doi_measure=_sel("doi_measure"),  # type: ignore[arg-type]
        performance_measure=_sel("performance_measure"),  # type: ignore[arg-type]
        icrv_regime=_sel("icrv_regime"),  # type: ignore[arg-type]
        dpl_phase=_sel("dpl_phase"),  # type: ignore[arg-type]
        cdai_score=_num("cdai_score"),
        extraction_confidence=float(_num("extraction_confidence") or 0.0),
        requires_verification=_bool("requires_verification"),
        pi_locked=_bool("pi_locked"),
        pi_notes=_extract_text(props.get("pi_notes", {})),
        extracted_at=_dt("extracted_at") or datetime.utcnow(),
        locked_at=_dt("locked_at"),
        notion_page_id=page_id,
    )


# ---------------------------------------------------------------------------
# NotionSync class
# ---------------------------------------------------------------------------


class NotionSync:
    """Bidirectional sync between the in-memory study store and a Notion DB.

    Args:
        token: Notion integration token (NOTION_TOKEN env var).
        database_id: Target Notion database ID (NOTION_DATABASE_ID env var).
    """

    def __init__(self, token: str, database_id: str) -> None:
        self._client = Client(auth=token)
        self._database_id = database_id

    def push_study(self, entry: StudyDatabaseEntry) -> str:
        """Create or update a study page in Notion.

        If ``entry.notion_page_id`` is already set, the existing page is
        updated; otherwise a new page is created.

        Args:
            entry: Fully populated and PI-locked study entry.

        Returns:
            The Notion page ID (new or existing).
        """
        props = _entry_to_properties(entry)

        try:
            if entry.notion_page_id:
                self._client.pages.update(
                    page_id=entry.notion_page_id,
                    properties=props,
                )
                logger.info("Updated Notion page %s", entry.notion_page_id)
                return entry.notion_page_id

            response: dict = self._client.pages.create(  # type: ignore[assignment]
                parent={"database_id": self._database_id},
                properties=props,
            )
            page_id: str = response["id"]
            logger.info("Created Notion page %s for study %s", page_id, entry.study_id)
            return page_id

        except APIResponseError as exc:
            logger.error(
                "Notion API error pushing study %s: %s", entry.study_id, exc
            )
            raise

    def update_study(self, page_id: str, updates: dict) -> None:
        """Apply partial property updates to an existing Notion page.

        ``updates`` is a mapping of StudyDatabaseEntry field names to new
        values; this method translates them to the Notion property format.

        Args:
            page_id: Notion page ID to update.
            updates: Dict of field_name → new_value pairs.
        """
        notion_props: dict[str, Any] = {}

        _text_fields = {
            "paper_title": "Paper Title",
            "authors": "Authors",
            "country": "Country",
            "study_id": "study_id",
            "pi_notes": "pi_notes",
        }
        _number_fields = {
            "year": "Year",
            "sample_n": "sample_n",
            "effect_r": "effect_r",
            "effect_t": "effect_t",
            "effect_beta": "effect_beta",
            "effect_df": "effect_df",
            "p_value": "p_value",
            "ci_lower": "ci_lower",
            "ci_upper": "ci_upper",
            "cdai_score": "cdai_score",
            "extraction_confidence": "extraction_confidence",
        }
        _select_fields = {
            "doi_measure": "doi_measure",
            "performance_measure": "performance_measure",
            "icrv_regime": "icrv_regime",
            "dpl_phase": "dpl_phase",
        }
        _bool_fields = {
            "requires_verification": "requires_verification",
            "pi_locked": "pi_locked",
        }
        _date_fields = {"extracted_at": "extracted_at", "locked_at": "locked_at"}

        for field, value in updates.items():
            if field in _text_fields:
                if field == "paper_title":
                    notion_props[_text_fields[field]] = _title(str(value))
                else:
                    notion_props[_text_fields[field]] = _text(str(value))
            elif field in _number_fields:
                notion_props[_number_fields[field]] = _number(value)
            elif field in _select_fields:
                notion_props[_select_fields[field]] = _select(value)
            elif field in _bool_fields:
                notion_props[_bool_fields[field]] = _checkbox(bool(value))
            elif field in _date_fields:
                notion_props[_date_fields[field]] = _date(
                    value if isinstance(value, datetime) else None
                )

        if not notion_props:
            logger.warning("update_study called with no translatable fields")
            return

        try:
            self._client.pages.update(page_id=page_id, properties=notion_props)
            logger.info("Partial update applied to Notion page %s", page_id)
        except APIResponseError as exc:
            logger.error("Notion API error updating page %s: %s", page_id, exc)
            raise

    def fetch_all_studies(self) -> list[StudyDatabaseEntry]:
        """Retrieve all study pages from the Notion database.

        Handles Notion's pagination automatically.

        Returns:
            List of StudyDatabaseEntry objects reconstructed from Notion pages.
        """
        entries: list[StudyDatabaseEntry] = []
        cursor: str | None = None

        while True:
            kwargs: dict[str, Any] = {"database_id": self._database_id}
            if cursor:
                kwargs["start_cursor"] = cursor

            try:
                response: dict = self._client.databases.query(**kwargs)  # type: ignore[assignment]
            except APIResponseError as exc:
                logger.error("Notion API error fetching studies: %s", exc)
                raise

            for page in response.get("results", []):
                try:
                    entry = _properties_to_entry(page["id"], page["properties"])
                    entries.append(entry)
                except (KeyError, ValueError) as exc:
                    logger.warning(
                        "Skipping Notion page %s due to parse error: %s",
                        page.get("id"),
                        exc,
                    )

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        logger.info("Fetched %d studies from Notion", len(entries))
        return entries
