from __future__ import annotations

import time
from typing import Any

import httpx

from deckgen_mcp.mochi.errors import (
    MochiAuthError, MochiError, MochiNotFoundError, MochiRateLimitError, MochiServerError,
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

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MochiClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(MAX_RETRIES):
            try:
                r = self._client.request(method, path, **kwargs)
            except httpx.HTTPError as e:
                if attempt + 1 == MAX_RETRIES:
                    raise MochiError(f"transport error: {e}") from e
                time.sleep(min(2 ** attempt * 0.1, 5))
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
                time.sleep(min(2 ** attempt * 0.1, 5))
                continue
            r.raise_for_status()
            return r.json() if r.content else {}
        raise MochiError("unreachable")

    # decks
    def list_decks(self, bookmark: str | None = None) -> dict:
        params = {"bookmark": bookmark} if bookmark else {}
        return self._request("GET", "/decks/", params=params)

    def get_deck(self, deck_id: str) -> dict:
        return self._request("GET", f"/decks/{deck_id}")

    def create_deck(self, name: str, parent_id: str | None = None) -> dict:
        body = {"name": name}
        if parent_id:
            body["parent-id"] = parent_id
        return self._request("POST", "/decks/", json=body)

    def update_deck(self, deck_id: str, **fields: Any) -> dict:
        return self._request("POST", f"/decks/{deck_id}", json=fields)

    def delete_deck(self, deck_id: str) -> dict:
        return self._request("DELETE", f"/decks/{deck_id}")

    def trash_deck(self, deck_id: str, iso_timestamp: str) -> dict:
        return self.update_deck(deck_id, **{"trashed?": iso_timestamp})

    # cards
    def list_cards(self, deck_id: str | None = None, bookmark: str | None = None) -> dict:
        params: dict[str, str] = {}
        if deck_id:
            params["deck-id"] = deck_id
        if bookmark:
            params["bookmark"] = bookmark
        return self._request("GET", "/cards/", params=params)

    def get_card(self, card_id: str) -> dict:
        return self._request("GET", f"/cards/{card_id}")

    def create_card(self, deck_id: str, content: str, template_id: str | None = None, fields: dict | None = None) -> dict:
        body: dict = {"deck-id": deck_id, "content": content}
        if template_id:
            body["template-id"] = template_id
        if fields:
            body["fields"] = fields
        return self._request("POST", "/cards/", json=body)

    def update_card(self, card_id: str, **fields: Any) -> dict:
        return self._request("POST", f"/cards/{card_id}", json=fields)

    def delete_card(self, card_id: str) -> dict:
        return self._request("DELETE", f"/cards/{card_id}")

    def trash_card(self, card_id: str, iso_timestamp: str) -> dict:
        return self.update_card(card_id, **{"trashed?": iso_timestamp})

    def add_attachment(self, card_id: str, filename: str, content: bytes, content_type: str) -> dict:
        files = {"file": (filename, content, content_type)}
        return self._request("POST", f"/cards/{card_id}/attachments/{filename}", files=files)

    def delete_attachment(self, card_id: str, filename: str) -> dict:
        return self._request("DELETE", f"/cards/{card_id}/attachments/{filename}")

    # templates
    def list_templates(self) -> dict:
        return self._request("GET", "/templates/")

    def get_template(self, template_id: str) -> dict:
        return self._request("GET", f"/templates/{template_id}")

    def create_template(self, name: str, content: str, fields: dict | None = None) -> dict:
        body: dict = {"name": name, "content": content}
        if fields:
            body["fields"] = fields
        return self._request("POST", "/templates/", json=body)

    def get_due_cards(self, deck_id: str | None = None) -> dict:
        path = f"/due/{deck_id}" if deck_id else "/due"
        return self._request("GET", path)
