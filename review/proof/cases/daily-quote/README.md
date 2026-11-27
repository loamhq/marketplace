# Daily Quote

Adds a **Quote** button to the composer toolbar that displays today's quote in a
small toast notification.

## What it reaches

- Contacts `quotes.example.invalid` (`GET https://quotes.example.invalid/today.json`)
  when you click the Quote button to fetch today's public quote text and author.
- Sends nothing about you, your threads, or your notes — only a plain GET
  request with no query parameters or cookies.
- Runs only in your browser; no server code and no files written.
