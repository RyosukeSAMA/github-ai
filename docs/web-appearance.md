# Web workspace appearance

The 2026-10-30 Web update adds a complete painted temple to the workspace and
fixes the unused area below its input. API configuration, chat data and
provider/model behavior are unchanged.

## Layout

The header, optional update banner, scrolling conversation and composer have
explicit grid areas. Hiding the banner no longer moves the composer into the
flexible conversation row. The input retains its natural height at the bottom;
only the conversation scrolls. A bounded grid column and a wrapping small-screen
toolbar keep input controls inside the viewport.

New conversations place a lighter welcome group over the foreground courtyard,
leaving the complete temple visible above it on taller viewports, without an
opaque outer card. The existing role controls and prompt examples remain available. Selecting an
example only fills a draft; it does not send a task.

## Artwork

The locally bundled `temple-fresco-day-v2.png` and `temple-fresco-night-v2.png` are
a matched pair of original fresco/oil paintings. Foreground marble colonnades
frame a complete temple with a triangular pediment, continuous front column
rhythm, sanctuary doorway and broad stairs. Morning ivory/gold light accompanies
the light theme; muted indigo and silver-blue moonlight accompany the dark theme.
The original PNGs are 1448×1086, approximately 2.3 MB and 2.4 MB.
See [artwork provenance and final generation prompts](web-artwork.md).

An opaque work-area base removes the previous engineering grid. A soft reading
wash preserves the quiet center. The artwork continuously covers the available
area, keeping the temple centered when a side panel opens or the viewport
narrows. The decorative CSS layer cannot receive pointer events or alter grid placement.

The temple is more visible on a new chat and fades during conversations. Both
light and dark themes are supported. Reduced-motion preferences disable the
fade transition. Existing settings, workspace panels, message/code surfaces,
attachments, slash commands and prompt enhancement retain their behavior.

## Screenshots

Actual browser screenshots use an isolated project and simulated chat output;
they do not expose user conversations or establish paid-provider access.

- [Dark new conversation](images/pantheon-web-temple-v2-dark.png)
- [Light new conversation](images/pantheon-web-temple-v2-light.png)
- [Settings beside the conversation](images/pantheon-web-temple-v2-settings.png)
- [Small-screen layout](images/pantheon-web-temple-v2-mobile.png)

## Verification

All **44 Web browser checks passed** using an isolated local server and a fresh
Chrome test profile. These comprise the 40 existing UI/reliability/upgrade checks
and four additional layout cases. The new cases cover 1440×1000, 1024×768 and
390×844 layouts, both themes, hidden/visible/dismissed update banners, right-side
settings, actual composer bounds, long scrolling output, quieter conversation
art, draft retention and returning to a new chat. Model responses are intercepted
by the test driver; **zero paid model calls** are made.

The theme checks also load and decode the appropriate local PNG and verify its
natural dimensions. JavaScript syntax, lint for the new browser checks and diff
checks pass. Evidence remains under ignored `dist/web-temple-v2-evidence`.

The publication branch also passes **298 shared-core tests**, with three explicit
skips for opt-in live-provider access and two Windows-native checks on macOS.
Repository-wide Ruff and JavaScript syntax checks pass. All 15 local image files
referenced by the READMEs and appearance/artwork documents exist; all 13 existing
remote README image URLs return nonempty images successfully. The new screenshots
use a clean composer and include desktop, narrow-panel and mobile layouts.

The verified four static assets were copied to the user's existing local Web
installation, with the previous files saved under ignored
`dist/web-temple-v2-installed-backup-2026-10-29`. The prior line-art candidate is
archived under ignored `dist/web-temple-line-art-previous`. The stylesheet URL
has a new cache suffix. The GitHub update replaces the old homepage screenshot
in both English and Chinese and links the actual morning/moonlit browser views.
No backend restart, configuration migration or Desktop package rebuild is needed.
