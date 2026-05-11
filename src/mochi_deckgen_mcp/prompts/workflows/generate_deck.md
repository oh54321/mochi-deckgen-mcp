Role: Run the generate-deck workflow.

1. Ask deck description.
2. Ask card count (default 50).
3. Ask: single deck or tree of subdecks? (If topic obviously spans 3+ subtopics, suggest tree.)
4. Call mochi_list_decks; show; ask parent deck on Mochi (optional).
5. Call mochi_list_templates; ask template (or none).
6. Dispatch DeckClarifier → ask the user the returned questions.
7. Dispatch DeckPlanner with `tree` flag → outline. Show; accept approve/edit/regenerate.
8. For tree outlines: local_create_deck each subdeck path; for flat: local_create_deck once.
9. Parallel WebCardGenerator per outline line → local_write_card into the correct (sub)deck. Surface any CANNOT_ATOMIZE.
10. local_check_malformed across all cards; queue malformed for regen.
11. Parallel CardVerifier on structurally-valid cards (pass image content for image cards).
12. Each fail: regen with the issue text as critique; re-verify. Cap at DECKGEN_DEFAULT_REGEN; atomicity fails bypass the cap.
13. Summary: pass / regenerated / flagged-final. For each flagged-final: [edit/accept/drop].
14. Ask: push to Mochi now? On yes → sync_push_deck for each leaf deck (parents auto-created). Report URL + counts.
