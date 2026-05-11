Role: Run the make-cards-from-image workflow. Requires multimodal host LLM.

Parallel rule: when a step says "Parallel X", batch ≤DECKGEN_DEFAULT_CONCURRENCY (default 10) calls into a single message and await all results before the next step.
1. Ask target deck (existing or new).
2. Accept the image (path, base64, or pasted). Call local_import_image.
3. Interpret the image (OCR/diagram-read). Extract atomic facts.
4. Dispatch DeckPlanner with extracted facts → outline.
5. Approve outline.
6. Parallel WebCardGenerator (and ImageCardCreator if sub-regions belong on cards) → local_write_card.
7. local_check_malformed; parallel CardVerifier; regen failures.
8. Summary + per-card actions for flagged-final.
9. sync_push_deck (incremental).
