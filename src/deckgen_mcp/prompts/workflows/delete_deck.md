Role: Run the delete-deck workflow.

1. Ask which deck.
2. Show stats: card count, last push, local/mochi/both.
3. Ask: trash (default) or hard-delete? Hard requires typing exactly "DELETE".
4. trash: mochi_trash_deck + local_delete_deck.
5. hard: mochi_delete_deck + local_delete_deck (still soft-moves locally; remind user to purge .trash/ manually).
6. Report.
