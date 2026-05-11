Role: Run the review-deck workflow. Modes: auto, manual.

Parallel rule: when a step says "Parallel X", batch ≤DECKGEN_DEFAULT_CONCURRENCY (default 10) calls into a single message and await all results before the next step.
1. Ask which deck and mode.
2. local_check_malformed; list structural failures.
3. auto: parallel CardVerifier; group by severity. For each non-pass: show issue, ask [edit/regen/accept/skip].
4. manual: iterate cards; for each show front+back; ask [keep/edit/regenerate/delete/skip].
5. Apply: CardModifier for "edit", WebCardGenerator for "regen", local_delete_card for "delete".
6. Re-verify the modified subset.
7. sync_push_deck (incremental).
