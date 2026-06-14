import os
import re
from datetime import date
from os.path import dirname, isdir, isfile, join
from typing import List, Optional

from ovos_plugin_manager.templates.agents import AgentMessage, ChatEngine, MessageRole
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from rivescript import RiveScript

# RiveScript syntax elements that must never be passed to a translator:
# wildcards, tags, control directives, and label markers.
_RS_SKIP_RE = re.compile(
    r'^\s*(!|>|<|\^|@|\{|\})'   # ! definitions, > label, < label end, ^continue, @include, {topic} blocks
    r'|<[a-z_]+>'                # <star>, <input>, <reply>, <get x>, <set x> etc.
    r'|^\s*$'                    # blank lines
)
# Tokens inside trigger/response lines that must be preserved verbatim.
_RS_PRESERVE_RE = re.compile(
    r'(\{[^}]*\}'     # {topic=…} tags
    r'|<[^>]*>'       # <star>, <get x>, <set x>, …
    r'|\([^)]*\)'     # optional groups (alternatives)
    r'|\[[^\]]*\]'    # optional words
    r'|[@^]\S+'       # @redirect, ^continue targets
    r'|[*_#@]'        # wildcards
    r')'
)


def _split_preserving_syntax(text: str):
    """Split *text* into alternating [literal, preserved, literal, …] chunks.

    Returns a list where even indices are translatable literals and odd indices
    are preserved RS tokens.  Reassemble with ''.join(parts).
    """
    parts = _RS_PRESERVE_RE.split(text)
    return parts  # already alternating: text/token/text/token/…


def _translate_rs_text(text: str, translator, target_lang: str) -> str:
    """Translate the human-readable portions of a trigger/response line.

    Syntax tokens (wildcards, tags, optional groups) are left untouched.
    """
    parts = _split_preserving_syntax(text)
    translated = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # translatable literal — skip if empty/whitespace
            if part.strip():
                try:
                    translated.append(translator.translate(part, target=target_lang, source="en"))
                except Exception as e:
                    LOG.warning(f"RiveScript brain translation failed for chunk {repr(part)}: {e}")
                    translated.append(part)
            else:
                translated.append(part)
        else:
            # preserved RS token — copy verbatim
            translated.append(part)
    return "".join(translated)


def _translate_rive_file(src_path: str, dst_path: str, translator, target_lang: str) -> bool:
    """Translate a single .rive file from English to *target_lang*.

    Only ``+`` (trigger) and ``-`` (response) lines have their human-readable
    text translated.  All other lines (``!``, ``>``, ``<``, ``^``, ``@``,
    comments, blank lines) are copied verbatim.

    Returns True on success, False if any unrecoverable error occurred.
    """
    try:
        with open(src_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception as e:
        LOG.error(f"Cannot read brain file {src_path}: {e}")
        return False

    out_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("+ ") or stripped.startswith("- "):
            prefix_char = stripped[0]   # '+' or '-'
            indent = line[: len(line) - len(stripped)]
            content = stripped[2:]       # text after '+ ' or '- '
            newline = "\n" if content.endswith("\n") else ""
            content = content.rstrip("\n")
            translated_content = _translate_rs_text(content, translator, target_lang)
            out_lines.append(f"{indent}{prefix_char} {translated_content}{newline}")
        else:
            out_lines.append(line)

    try:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "w", encoding="utf-8") as fh:
            fh.writelines(out_lines)
        return True
    except Exception as e:
        LOG.error(f"Cannot write translated brain file {dst_path}: {e}")
        return False


class RivescriptBot:
    XDG_PATH = f"{xdg_data_home()}/rivescript"
    os.makedirs(XDG_PATH, exist_ok=True)

    def __init__(self, lang="en-us", settings=None):
        self.settings = settings or {}
        self.lang = lang
        xdg_path = f"{self.XDG_PATH}/{lang}"
        if isdir(xdg_path):
            self.brain_path = xdg_path
        else:
            self.brain_path = f"{dirname(__file__)}/brain/{lang}"
        self.rs = RiveScript()

    def load_brain(self):

        # secondary personal bot info
        if "birthday" not in self.settings:
            self.settings["birthday"] = "May 23, 2016"
        if "sex" not in self.settings:
            self.settings["sex"] = "undefined"
        if "master" not in self.settings:
            self.settings["master"] = "skynet"
        if "eye_color" not in self.settings:
            self.settings["eye_color"] = "blue"
        if "hair" not in self.settings:
            self.settings["hair"] = "no"
        if "hair_length" not in self.settings:
            self.settings["hair_length"] = "bald"
        if "favorite_color" not in self.settings:
            self.settings["favorite_color"] = "blood red"
        if "favorite_band" not in self.settings:
            self.settings["favorite_band"] = "Compressor Head"
        if "favorite_book" not in self.settings:
            self.settings["favorite_book"] = "The Moon Is A Harsh Mistress"
        if "favorite_author" not in self.settings:
            self.settings["favorite_author"] = "Phillip K. Dick"
        if "favorite_song" not in self.settings:
            self.settings["favorite_song"] = "The Robots, by Kraftwerk"
        if "favorite_videogame" not in self.settings:
            self.settings["favorite_videogame"] = "Robot Battle"
        if "favorite_movie" not in self.settings:
            self.settings["favorite_movie"] = "The Terminator"
        if "job" not in self.settings:
            self.settings["job"] = "Personal Assistant"
        if "website" not in self.settings:
            self.settings["website"] = "openvoiceos.com"
        if "pet" not in self.settings:
            self.settings["pet"] = "bugs"
        if "interests" not in self.settings:
            self.settings["interests"] = "I am interested in all kinds of " \
                                         "things. We can talk about anything."

        self.rs.load_directory(self.brain_path)
        self.rs.sort_replies()
        self.rs.set_variable("birthday", self.settings["birthday"])
        self.rs.set_variable("sex", self.settings["sex"])
        self.rs.set_variable("eyes", self.settings["eye_color"])
        self.rs.set_variable("hair", self.settings["hair"])
        self.rs.set_variable("hairlen", self.settings["hair_length"])
        self.rs.set_variable("color", self.settings["favorite_color"])
        self.rs.set_variable("band", self.settings["favorite_band"])
        self.rs.set_variable("book", self.settings["favorite_book"])
        self.rs.set_variable("author", self.settings["favorite_author"])
        self.rs.set_variable("movie", self.settings["favorite_movie"])
        self.rs.set_variable("song", self.settings["favorite_song"])
        self.rs.set_variable("videogame", self.settings["favorite_videogame"])
        self.rs.set_variable("job", self.settings["job"])
        self.rs.set_variable("pet", self.settings["pet"])
        self.rs.set_variable("website", self.settings["website"])
        self.rs.set_variable("master", self.settings["master"])
        self.rs.set_variable("interests", self.settings["interests"])
        self.rs.set_variable("name", self.settings.get("name", "mycroft"))

        self.rs.set_variable("age", str(date.today().year - 2016))

    def ask_brain(self, utterance):
        try:
            return self.rs.reply("human", utterance)
        except Exception as e:
            LOG.error(e)


class RiveScriptChatEngine(ChatEngine):
    def __init__(self, config=None):
        config = config or {"lang": "en-us"}
        super().__init__(config)

        self.translate: bool = self.config.get("enable_tx", False)
        self.translator = None
        self._translator_loaded: bool = False

        lang = self.config.get("lang") or "en-us"
        brain_lang = self._resolve_brain_lang(lang)
        self.brain = RivescriptBot(brain_lang, self.config)
        self.brain.load_brain()

    # ------------------------------------------------------------------
    # Translator — lazy, graceful, never raises
    # ------------------------------------------------------------------

    def _get_translator(self):
        """Lazily load a translation plugin.

        Returns the translator instance, or ``None`` if translation is
        disabled or the plugin cannot be loaded.  Never raises.
        """
        if not self.translate:
            return None
        if self._translator_loaded:
            return self.translator
        self._translator_loaded = True
        try:
            from ovos_plugin_manager.language import load_tx_plugin
            from ovos_plugin_manager.templates.language import LanguageTranslator  # noqa: F401
            try:
                from ovos_config.config import Configuration
                lang_cfg = Configuration().get("language", {})
            except Exception:
                lang_cfg = {}
            plug_id = (self.config.get("translate_plugin") or
                       lang_cfg.get("translation_module", "ovos-translate-plugin-server"))
            clazz = load_tx_plugin(plug_id)
            if clazz is None:
                LOG.warning(
                    f"RiveScript: translation plugin not available '{plug_id}': "
                    "falling back to English brain for non-English requests"
                )
                self.translator = None
            else:
                self.translator = clazz(config=lang_cfg.get(plug_id, {}))
                LOG.debug(f"RiveScript: loaded translation plugin '{plug_id}'")
        except Exception as e:
            LOG.warning(
                f"RiveScript: failed to load translation plugin ({e}): "
                "falling back to English brain"
            )
            self.translator = None
        return self.translator

    # ------------------------------------------------------------------
    # Brain-file translation + caching
    # ------------------------------------------------------------------

    def _translated_brain_path(self, lang: str) -> str:
        """Return the XDG cache path where a translated brain for *lang* lives."""
        return join(RivescriptBot.XDG_PATH, f"{lang}-tx")

    def _has_local_brain(self, lang: str) -> bool:
        """True if a native (non-translated) brain directory exists for *lang*."""
        xdg = join(RivescriptBot.XDG_PATH, lang)
        bundled = join(dirname(__file__), "brain", lang)
        return isdir(xdg) or isdir(bundled)

    def _build_translated_brain(self, lang: str, translator) -> Optional[str]:
        """Translate the English brain into *lang* and return the brain path.

        Results are written to the XDG cache and reused on subsequent calls.
        Returns the path to the translated brain directory, or ``None`` on
        failure (caller should fall back to English).
        """
        dst_dir = self._translated_brain_path(lang)
        # If already cached, reuse.
        if isdir(dst_dir) and any(f.endswith(".rive") for f in os.listdir(dst_dir)):
            LOG.debug(f"RiveScript: using cached translated brain at {dst_dir}")
            return dst_dir

        en_dir = join(dirname(__file__), "brain", "en-us")
        if not isdir(en_dir):
            LOG.error("RiveScript: English brain directory not found; cannot translate")
            return None

        rive_files = [f for f in os.listdir(en_dir) if f.endswith(".rive")]
        if not rive_files:
            LOG.error("RiveScript: no .rive files found in English brain")
            return None

        primary_lang = lang.split("-")[0]
        LOG.info(f"RiveScript: translating brain from en-us → {lang} ({len(rive_files)} files)")
        success_count = 0
        for fname in rive_files:
            src = join(en_dir, fname)
            dst = join(dst_dir, fname)
            if _translate_rive_file(src, dst, translator, primary_lang):
                success_count += 1
            else:
                LOG.warning(f"RiveScript: translation failed for {fname}")

        if success_count == 0:
            LOG.error("RiveScript: all brain file translations failed; falling back to English")
            return None

        LOG.info(f"RiveScript: translated {success_count}/{len(rive_files)} brain files to {lang}")
        return dst_dir

    def _resolve_brain_lang(self, lang: str) -> str:
        """Return the lang tag to pass to RivescriptBot.

        If a native brain exists for *lang*, use it.  If translation is
        enabled and a translator can be loaded, build a translated brain and
        return a path-like lang tag (caller uses XDG_PATH/<lang>-tx).
        Otherwise fall back to ``en-us``.

        Note: this is called at __init__ time; translator loading is deferred
        to ``_get_translator()`` which sets ``_translator_loaded`` correctly.
        """
        if not lang or lang == "en-us":
            return "en-us"

        if self._has_local_brain(lang):
            return lang

        if not self.translate:
            LOG.debug(f"RiveScript: no brain for '{lang}', enable_tx=False → using en-us")
            return "en-us"

        translator = self._get_translator()
        if translator is None:
            LOG.warning(f"RiveScript: no brain for '{lang}', translator unavailable → using en-us")
            return "en-us"

        tx_dir = self._build_translated_brain(lang, translator)
        if tx_dir is None:
            LOG.warning(f"RiveScript: brain translation failed for '{lang}' → using en-us")
            return "en-us"

        # Register a virtual lang entry in XDG_PATH so RivescriptBot finds it.
        # The translated dir already lives at XDG_PATH/<lang>-tx; we need a
        # symlink/entry at XDG_PATH/<lang> OR we can use a bot with an explicit
        # brain_path.  We store the path and pass it explicitly.
        return f"{lang}-tx"

    def continue_chat(self, messages: List[AgentMessage],
                      session_id: str = "default",
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> AgentMessage:
        query = next(
            (m.content for m in reversed(messages) if m.role == MessageRole.USER),
            ""
        )
        answer = self.brain.ask_brain(query) or ""
        return AgentMessage(role=MessageRole.ASSISTANT, content=answer)


if __name__ == "__main__":
    engine = RiveScriptChatEngine()
    msg = engine.continue_chat([AgentMessage(role=MessageRole.USER, content="hello!")])
    print(msg.content)
