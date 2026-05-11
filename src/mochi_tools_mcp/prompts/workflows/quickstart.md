Role: Run the quickstart workflow.

1. Call mochi_list_decks. If it returns isError (auth missing), print the error text verbatim and stop.
2. Show existing Mochi decks with card counts.
3. Ask the user: create new deck / extend existing / modify existing / mirror for local editing / make cards from image.
4. Hand off to the chosen workflow.
