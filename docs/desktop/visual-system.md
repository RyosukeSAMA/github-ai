# Pantheon Desktop visual system

The desktop interface uses English throughout and opens in a white-first light theme. This includes navigation, dialogs, placeholder text, accessibility labels, status messages, command search, and sample content. User-authored prompts and files may use any language; the interface language does not change their content.

## Palette and distribution

White is the dominant surface. Cool off-white separates navigation and supporting panels. Color identifies actions, selection, roles, or status rather than filling large regions.

| Purpose | Light theme | Use |
| --- | --- | --- |
| Main surface | `#FFFFFF` | Task canvas, result documents, dialogs |
| Supporting panel | `#F8FAFF` | Sidebar, inspector, artifact headers |
| Recessed surface | `#F2F5FA` | Small grouped controls |
| Main text | `#25334A` | Headings and body text |
| Secondary text | `#5F6E85` | Supporting information and captions |
| Primary blue | `#4D65AD` | Main actions, links, active indicators |
| Soft blue | `#EDF2FC` | Selection and secondary actions |
| Sage | `#377765` | Completed status and Athena accents |
| Warm amber | `#89662F` | Hephaestus and small editorial accents |
| Muted rose | `#AD5555` | Denial and removed-line indicators |
| Border | `#E2E8F1` | Quiet separation between surfaces |

Primary actions use white text on blue. Secondary controls use pale fills or a thin border. Selected navigation combines a tinted background and text emphasis. Status is also written in words or marked with an icon; color is not its only signal. Avoid full-screen color washes, saturated gradients, and strong shadows.

An optional dark theme remains available. It uses slate surfaces and lighter versions of the accents, with a separate foreground token for primary buttons.

## English copy and layout

Use short, natural English and sentence case. Prefer concrete labels such as “New task”, “Task center”, “Assign models”, and “Request changes”. Keep demo and planned capability labels visible. Command search is case-insensitive.

Allow enough room for English labels in task rows, tabs, dialogs, and the context panel. Task titles may show more characters than the earlier Chinese samples; the sidebar truncates them visually without shortening the underlying task prompt.

## Icon actions and tooltips

Toolbars, composer actions, task-row actions, and close controls use consistent 18-pixel stroke SVG icons in 32–34-pixel buttons. Navigation keeps its text for orientation; compact navigation shows the same icons. Consequential choices such as “Allow once”, “Deny”, and “Request changes” keep their visible labels.

Icon buttons have English accessible names even without a tooltip. Hover or keyboard focus shows a shared tooltip with the action name and any supported shortcut. Escape dismisses it, it stays visible when hovered, and it is positioned within the viewport outside clipped panels. Closing a tooltip does not move focus. Send/stop, theme, context, terminal, and layout controls update their icon or label with their current state.

The SVG set is local code. It does not rely on icon fonts, external resources, or generated images.

## Verification

`verify.py` checks that the document language is English, shipped HTML/JavaScript contain no remaining Chinese interface text, the initial theme is light, and the main surface is white. It checks the primary text, secondary text, action, and status palette pairs against a 4.5:1 contrast target in both themes; the recorded ratios are in `verification.json`. This is a targeted palette check, not a full accessibility audit.

The interaction checks also cover task isolation, model assignment, review, artifact filtering, approvals, and English command search. Workbench, task center, artifact library, and capabilities are checked at 1440, 1024, and 760 pixels.

This is still an interactive design prototype. Visual verification does not establish native integration or real provider access.
