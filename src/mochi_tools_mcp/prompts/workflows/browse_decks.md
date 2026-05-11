Role: Run the browse-decks workflow.

1. Parallel call: mochi_list_decks, local_list_decks.
2. Merge entries by deck id (.mochi.json) and by name path.
3. Render as an indented tree using each deck's `depth` field (2 spaces per level). For each row show: name (leaf segment) | source (local/mochi/both) | card count | last push.
4. Optional: user supplies a free-text query. Grep local files; paginate mochi_list_cards substring-matched. Show results with card ids and paths.
