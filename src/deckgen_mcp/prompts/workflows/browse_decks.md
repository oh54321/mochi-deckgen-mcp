Role: Run the browse-decks workflow.

1. Parallel call: mochi_list_decks, local_list_decks.
2. Merge by deck id from .mochi.json mappings.
3. Show table: name | source (local/mochi/both) | card count | last push | parent.
4. Optional: user supplies a free-text query. Grep local files; paginate mochi_list_cards substring-matched. Show results with card ids and paths.
