# Desktop provider marks

The desktop preview uses small, locally bundled provider marks in connection
selectors, model menus, saved connections and configured role assignments.
Watercolor portraits continue to identify Pantheon roles. Logos identify the
selected connection type, not API verification, endorsement or a task's recorded
execution. Model availability still comes from the existing catalog and explicit
API tests. Custom IDs and unknown providers remain supported.

## Sources

Retrieved on 2026-10-27. The files retain the supplied artwork and colors; the
DeepSeek favicon was converted to PNG without redrawing. All names and marks
belong to their respective owners; Pantheon's MIT license does not grant rights
to third-party trademarks. Review the applicable brand terms before broader
distribution. This local preview does not establish brand approval.

| Bundled file | Official source |
| --- | --- |
| `provider-deepseek.png` | <https://www.deepseek.com/favicon.ico> |
| `provider-openai.png` | <https://github.com/openai.png?size=128> (official OpenAI organization avatar) |
| `provider-anthropic.png` | <https://www.anthropic.com/images/icons/apple-touch-icon.png> |
| `provider-ollama.svg` | <https://github.com/ollama/ollama/blob/main/docs/ollama-logo.svg> |

Usage guidance: [OpenAI](https://openai.com/brand/) and
[Anthropic](https://www.anthropic.com/legal/trademark-guidelines).

No image is fetched at runtime. A missing image or unknown provider uses a
neutral connection glyph while retaining its text label. Ollama is presented as
a model runtime; a local label is shown only for an explicit loopback endpoint.
Non-default API hosts are described as custom endpoints. New model versions use
the same provider mark without changing saved model choices.


## Actual local preview

The macOS arm64 beta.15 screenshots were captured from the packaged application
using dummy credentials in an isolated project. Their model choices illustrate
configuration, not verified commercial-provider access.

- [Role assignments, light](provider-roles-light.png)
- [Role assignments, dark](provider-roles-dark.png)
- [Connection settings](provider-connections-light.png)
- [Model menu](provider-model-menu.png)
