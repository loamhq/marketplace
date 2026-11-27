# Thread Tagger

<!-- loam:hero -->
Suggests short topic tags for your threads so you can find them again later.
<!-- /loam:hero -->

Thread Tagger reads your threads in the page and picks out the words that make each one different from the others. It shows up to three tags per thread. It is plain word counting, with no AI model.

## Where you see it

- **Chats:** a single line above your agents shows the topics of your ten most recent threads.
- **A thread:** under the header, its suggested tags appear as small chips. Press one to keep it on the thread.

## How tags are picked

1. The thread's words are lower-cased, and common words ("the", "thanks", "please"...) are dropped.
2. Words that appear at least twice are scored by how often they appear here and how rare they are in your other recent threads.
3. The top three become the suggestions.

Kept tags are remembered so the same tags show up wherever you are signed in.

## What it reaches

- It reads your conversation records to count words.
- No memory, no server code.

## Changelog

- 1.0.0: first release.
