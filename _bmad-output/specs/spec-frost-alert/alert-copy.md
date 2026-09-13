# Alert copy

Voice rules for frost alerts. Exact strings are not locked; the split below is.

## Notification preview (lock screen / shade)

Must be understandable in one glance, without opening the chat. Uses emojis. States that frost risk is coming and roughly how soon (24h / 12h / 6h).

Does **not** need the full forecast table, location string, or ack instructions.

## Opened message

Adds the facts the preview omitted: configured location, first-crossing temperature in the user's scale, when that crossing is expected, the user's threshold, and a clear ack control ("plants are in overwintering" — `/in` or `plants_in`).

## Out of scope for this companion

Watchdog-miss copy (CAP-7) is a separate warning, not a frost alert. Same preview-first rule applies if we later specify it; not locked here.
