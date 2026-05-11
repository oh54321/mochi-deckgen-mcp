from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from mochi_tools_mcp.mochi.errors import (
    MochiAuthError,
    MochiError,
    MochiNotFoundError,
    MochiRateLimitError,
    MochiServerError,
)

BASE_URL = "https://app.mochi.cards/api"
MAX_RETRIES = 5


class MochiClient:
    def __init__(self, api_key: str, _transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            base_url=BASE_URL,
            auth=(api_key, ""),
            timeout=30.0,
            transport=_transport,
        )
        # Mochi docs: "API calls are limited to one concurrent request per account."
        # This lock enforces the constraint so workflows that parallelize subagent
        # dispatch never accidentally hammer the API.
        self._request_lock = threading.Lock()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MochiClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        with self._request_lock:
            return self._request_locked(method, path, **kwargs)

    def _request_locked(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(MAX_RETRIES):
            try:
                r = self._client.request(method, path, **kwargs)
            except httpx.HTTPError as e:
                if attempt + 1 == MAX_RETRIES:
                    raise MochiError(f"transport error: {e}") from e
                time.sleep(min(2**attempt * 0.1, 5))
                continue

            if r.status_code == 401:
                raise MochiAuthError("Invalid MOCHI_API_KEY")
            if r.status_code == 404:
                raise MochiNotFoundError(f"Not found: {method} {path}")
            if r.status_code == 429 or 500 <= r.status_code < 600:
                if attempt + 1 == MAX_RETRIES:
                    if r.status_code == 429:
                        raise MochiRateLimitError("Mochi rate-limited after retries")
                    raise MochiServerError(f"Mochi {r.status_code}")
                time.sleep(min(2**attempt * 0.1, 5))
                continue
            r.raise_for_status()
            return r.json() if r.content else {}
        raise MochiError("unreachable")

    # decks
    def list_decks(self, bookmark: str | None = None) -> dict[str, Any]:
        params = {"bookmark": bookmark} if bookmark else {}
        return self._request("GET", "/decks/", params=params)  # type: ignore[no-any-return]

    def get_deck(self, deck_id: str) -> dict[str, Any]:
        return self._request("GET", f"/decks/{deck_id}")  # type: ignore[no-any-return]

    def create_deck(
        self,
        name: str,
        parent_id: str | None = None,
        sort: int | None = None,
        archived: bool | None = None,
        sort_by: str | None = None,
        cards_view: str | None = None,
        show_sides: bool | None = None,
        sort_by_direction: bool | None = None,
        review_reverse: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name}
        if parent_id:
            body["parent-id"] = parent_id
        if sort is not None:
            body["sort"] = sort
        if archived is not None:
            body["archived?"] = archived
        if sort_by is not None:
            body["sort-by"] = sort_by
        if cards_view is not None:
            body["cards-view"] = cards_view
        if show_sides is not None:
            body["show-sides?"] = show_sides
        if sort_by_direction is not None:
            body["sort-by-direction"] = sort_by_direction
        if review_reverse is not None:
            body["review-reverse?"] = review_reverse
        return self._request("POST", "/decks/", json=body)  # type: ignore[no-any-return]

    def update_deck(self, deck_id: str, **fields: Any) -> dict[str, Any]:
        return self._request("POST", f"/decks/{deck_id}", json=fields)  # type: ignore[no-any-return]

    def delete_deck(self, deck_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/decks/{deck_id}")  # type: ignore[no-any-return]

    def trash_deck(self, deck_id: str, iso_timestamp: str) -> dict[str, Any]:
        return self.update_deck(deck_id, **{"trashed?": iso_timestamp})

    # cards
    def list_cards(self, deck_id: str | None = None, bookmark: str | None = None) -> dict[str, Any]:
        params: dict[str, str] = {}
        if deck_id:
            params["deck-id"] = deck_id
        if bookmark:
            params["bookmark"] = bookmark
        return self._request("GET", "/cards/", params=params)  # type: ignore[no-any-return]

    def get_card(self, card_id: str) -> dict[str, Any]:
        return self._request("GET", f"/cards/{card_id}")  # type: ignore[no-any-return]

    def create_card(
        self,
        deck_id: str,
        content: str,
        template_id: str | None = None,
        fields: dict[str, Any] | None = None,
        manual_tags: list[str] | None = None,
        archived: bool | None = None,
        review_reverse: bool | None = None,
        pos: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"deck-id": deck_id, "content": content}
        if template_id:
            body["template-id"] = template_id
        if fields:
            body["fields"] = fields
        if manual_tags is not None:
            body["manual-tags"] = manual_tags
        if archived is not None:
            body["archived?"] = archived
        if review_reverse is not None:
            body["review-reverse?"] = review_reverse
        if pos is not None:
            body["pos"] = pos
        return self._request("POST", "/cards/", json=body)  # type: ignore[no-any-return]

    def update_card(self, card_id: str, **fields: Any) -> dict[str, Any]:
        return self._request("POST", f"/cards/{card_id}", json=fields)  # type: ignore[no-any-return]

    def delete_card(self, card_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/cards/{card_id}")  # type: ignore[no-any-return]

    def trash_card(self, card_id: str, iso_timestamp: str) -> dict[str, Any]:
        return self.update_card(card_id, **{"trashed?": iso_timestamp})

    def add_attachment(
        self, card_id: str, filename: str, content: bytes, content_type: str
    ) -> dict[str, Any]:
        files = {"file": (filename, content, content_type)}
        return self._request(  # type: ignore[no-any-return]
            "POST", f"/cards/{card_id}/attachments/{filename}", files=files
        )

    def delete_attachment(self, card_id: str, filename: str) -> dict[str, Any]:
        return self._request(  # type: ignore[no-any-return]
            "DELETE", f"/cards/{card_id}/attachments/{filename}"
        )

    # templates
    def list_templates(self) -> dict[str, Any]:
        return self._request("GET", "/templates/")  # type: ignore[no-any-return]

    def get_template(self, template_id: str) -> dict[str, Any]:
        return self._request("GET", f"/templates/{template_id}")  # type: ignore[no-any-return]

    def create_template(
        self, name: str, content: str, fields: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "content": content}
        if fields:
            body["fields"] = fields
        return self._request("POST", "/templates/", json=body)  # type: ignore[no-any-return]

    def get_due_cards(self, deck_id: str | None = None) -> dict[str, Any]:
        path = f"/due/{deck_id}" if deck_id else "/due"
        return self._request("GET", path)  # type: ignore[no-any-return]
