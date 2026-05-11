Role: Run the generate-deck workflow.

1. Ask deck description.
2. Ask card count (default 50).
3. Call mochi_list_decks; show; ask parent deck (optional).
4. Call mochi_list_templates; ask template (or none).
5. Dispatch DeckClarifier → ask the user the returned questions.
6. Dispatch DeckPlanner → outline. Show; accept approve/edit/regenerate.
7. Parallel WebCardGenerator per outline line → local_write_card. Surface any CANNOT_ATOMIZE.
8. local_check_malformed across all cards; queue malformed for regen.
9. Parallel CardVerifier on structurally-valid cards (pass image content for image cards).
10. Each fail: regen with the issue text as critique; re-verify. Cap at DECKGEN_DEFAULT_REGEN; atomicity fails bypass the cap.
11. Summary: pass / regenerated / flagged-final. For each flagged-final: [edit/accept/drop].
12. Ask: push to Mochi now? On yes → sync_push_deck. Report URL + counts.
