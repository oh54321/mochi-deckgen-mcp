Role: Run the mirror-deck workflow.

1. Disclose: "Mochi's API does not expose attachment downloads. This mirror preserves image references but not the binaries. Continue?"
2. Call mochi_list_decks → numbered list. User picks by index or name.
3. sync_pull_deck on the chosen deck_id.
4. Report cards pulled + any missing images. Point to attachments-not-downloaded.txt.
