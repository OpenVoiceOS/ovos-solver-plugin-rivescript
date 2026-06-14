# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/robot.svg' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Rivescript Chatbot

Give OVOS some sass with RiveScript!

Leverages `.rive` brain files to create fun, persona-driven interactions.  Phrases not explicitly handled by other skills will be handled by the chatbot, so nearly every interaction will have _some_ response.

## Examples

* "Do you like ice cream"
* "Do you like dogs"
* "I have a jump rope"
* "hello"
* "what is your name"

## Usage

ChatEngine API backed by a RiveScript brain:

```python
from ovos_plugin_manager.templates.agents import AgentMessage, MessageRole
from ovos_solver_rivescript_plugin import RiveScriptChatEngine

engine = RiveScriptChatEngine()
reply = engine.continue_chat([AgentMessage(role=MessageRole.USER, content="hello")])
print(reply.content)
# Hi there!
```

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `lang` | `"en-us"` | Brain language to load.  Must match a directory under `brain/` or the XDG data dir. |
| `enable_tx` | `False` | Opt-in brain-file translation (see below). |
| `translate_plugin` | `"ovos-translate-plugin-server"` | Translation plugin ID to use when `enable_tx` is on. |

### Opt-in brain-file translation (`enable_tx`)

By default the plugin only supports English (`en-us`).  Setting `enable_tx: true` lets the plugin serve non-English users by translating the bundled English `.rive` brain into the requested language.

```json
{
  "ovos-solver-rivescript-plugin": {
    "lang": "pt-pt",
    "enable_tx": true,
    "translate_plugin": "ovos-translate-plugin-server"
  }
}
```

**How it works:**

1. When `lang` is requested and no native `.rive` brain exists for it, the plugin translates the English brain into the target language.
2. Only human-readable text in trigger lines (`+ …`) and response lines (`- …`) is translated.  RiveScript control syntax — wildcards (`*`, `_`), tags (`<star>`, `<get>`, `<set>`, `{topic=…}`, …), optional groups (`[…]`, `(…)`), label markers (`>`, `<`), definitions (`!`), and redirects (`@`, `^`) — is preserved verbatim.
3. The translated `.rive` files are cached in the XDG data directory (`~/.local/share/rivescript/<lang>-tx/`) and reused on subsequent runs without re-translating.
4. If the translator cannot be loaded or translation fails, the plugin falls back to the English brain without crashing.

**Recommended translate plugin:** `ovos-translate-plugin-server` (the default) or another remote plugin.  Translation plugins may be instantiated multiple times across different personas, so local model plugins that load a large model into memory on each instantiation are costly.  A remote plugin delegates inference to a server and avoids this overhead.

**Default behaviour is unchanged:** with `enable_tx` off (the default), no translator is loaded, the English brain is used, and there is no runtime cost.
