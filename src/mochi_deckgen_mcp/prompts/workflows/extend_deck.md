Role: Run the extend-deck workflow.

1. Ask which deck (call local_list_decks + mochi_list_decks for picker).
2. Parallel CardCompressor over existing cards → dedup summaries.
3. Ask what to add (free text, count).
4. Dispatch DeckPlanner with existing-card summaries in context → outline avoiding duplicates.
5. Approve outline.
6. Parallel WebCardGenerator → local_write_card with new indices (max existing + 1, …).
7. local_check_malformed; queue malformed for regen.
8. Parallel CardVerifier; regen failures up to DECKGEN_DEFAULT_REGEN; atomicity bypasses cap.
9. Summary table. Per-card [edit/accept/drop] on flagged-final.
10. sync_push_deck (incremental). Report counts.
