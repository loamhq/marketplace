# Translate Inline

<!-- loam:hero -->
Translate a selected passage of any reply into your language without leaving the thread.
<!-- /loam:hero -->

When an agent answers in a language you read less easily, select the part you want, press **Translate**, and the translation appears in a small card next to it.

## Setting up

1. Get an API key from Lingvo.
2. In Loam, open Settings › Connections › API keys and paste it under Lingvo.
3. Turn Translate Inline on in Settings › Plugins.

## Using it

- Select text inside a reply. A small **Translate** button appears beside it.
- Press it. The card shows the translation, and the language it was translated from when Lingvo detects one.
- Press Escape or click elsewhere to close the card.

It translates into your browser's language. Passages are limited to about 4,000 characters.

## What leaves your server

Only the passage you select is sent to `api.lingvo.example.invalid`, with your Lingvo key. Nothing is saved by the plugin.

## If something goes wrong

The card says what happened in plain words: no key yet, a key Lingvo did not accept, Lingvo being busy, or the plugin still starting.

## Changelog

- 1.0.0: first release.
