Role: Run the merge-decks workflow.

Parallel rule: when a step says "Parallel X", batch ≤DECKGEN_DEFAULT_CONCURRENCY (default 10) calls into a single message and await all results before the next step.
1. Ask deck A, deck B, target name, drop duplicates?, parent on Mochi?
2. Parallel CardCompressor on all cards in both decks.
3. Compare summaries; flag near-duplicates. For each conflict: ask user which copy to keep or merge.
4. local_create_deck target; local_write_card for the merged set.
5. sync_push_deck.
6. Ask: trash the originals? On yes → mochi_trash_deck for each, local_delete_deck for each.
