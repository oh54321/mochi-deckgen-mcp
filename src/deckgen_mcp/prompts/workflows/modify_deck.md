Role: Run the modify-deck workflow. Presets: swap-sides, to-cloze, make-harder, add-tags, freeform.

1. Ask which deck and which transformation (preset or freeform description).
2. Ask scope: all / by tag / by content match. local_list_cards to confirm.
3. Pick 3 representative cards in scope.
4. Parallel CardModifier on the 3 samples → show before/after diff.
5. User: approve / adjust wording / abort. For global presets (e.g. swap-sides), require a second confirmation.
6. Parallel CardModifier on full scope. Skip and warn on REFUSED outputs.
7. Parallel CardVerifier; revert any card whose modified version fails atomicity.
8. Summary of changed / reverted / flagged.
9. sync_push_deck (incremental).
