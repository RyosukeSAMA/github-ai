---
name: build-web-preview
description: Design and implement a complete responsive webpage that Pantheon can preview directly. Use for landing pages, portfolios, dashboards, prototypes, and HTML UI requests.
---

# Build Web Preview

Apollo owns visual direction and Hephaestus owns implementation quality.

## Workflow

1. Infer the audience, primary workflow, content hierarchy, and required states.
2. Choose a restrained visual system appropriate to the product instead of a
   generic AI landing-page style.
3. Produce a complete responsive document with accessible semantics.
4. Use real content and working links supplied by the user.
5. Include interaction states expected for the requested experience.
6. Check narrow and wide layouts conceptually before returning the artifact.
7. Return the final page in one fenced `html` block so Pantheon Preview can open it.

Prefer a self-contained HTML document with inline CSS and JavaScript unless the
user requests a project structure. Do not claim external assets are available
unless they are embedded or referenced by a valid URL.
