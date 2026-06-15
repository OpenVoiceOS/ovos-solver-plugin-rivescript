"""Unit tests for opt-in brain-file translation (enable_tx).

No network access, no real translation plugin required — a mock translator
is injected directly to exercise the translate-and-cache path.
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from ovos_plugin_manager.templates.agents import AgentMessage, ChatEngine, MessageRole
from ovos_solver_rivescript_plugin import RiveScriptChatEngine
from ovos_solver_rivescript_plugin import (
    _translate_rs_text,
    _translate_rive_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_translator(lang_map: dict):
    """Return a mock translator whose .translate() method uses *lang_map*."""
    tx = MagicMock()

    def _translate(text, target, source="en"):
        return lang_map.get(text.strip(), f"[{target}]{text}")

    tx.translate.side_effect = _translate
    return tx


# ---------------------------------------------------------------------------
# translate-text helpers
# ---------------------------------------------------------------------------

class TestTranslateRsText:
    def test_plain_text_translated(self):
        tx = _fake_translator({"hello": "olá"})
        result = _translate_rs_text("hello", tx, "pt")
        assert result == "olá"

    def test_wildcard_preserved(self):
        tx = _fake_translator({})
        result = _translate_rs_text("tell me about *", tx, "pt")
        # '*' wildcard must survive; literal parts get translated (or echoed)
        assert "*" in result

    def test_tag_preserved(self):
        tx = _fake_translator({})
        result = _translate_rs_text("you said <star>", tx, "pt")
        assert "<star>" in result

    def test_empty_preserves(self):
        tx = _fake_translator({})
        result = _translate_rs_text("", tx, "pt")
        assert result == ""


class TestTranslateRiveFile:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_trigger_and_response_translated(self):
        src = os.path.join(self.tmp, "test.rive")
        dst = os.path.join(self.tmp, "out", "test.rive")
        with open(src, "w") as fh:
            fh.write("! version = 2.0\n+ hello\n- hi there\n")
        tx = _fake_translator({"hello": "olá", "hi there": "olá aí"})
        ok = _translate_rive_file(src, dst, tx, "pt")
        assert ok
        with open(dst) as fh:
            content = fh.read()
        assert "+ olá" in content
        assert "- olá aí" in content
        assert "! version = 2.0" in content  # definition line untouched

    def test_definition_lines_untouched(self):
        src = os.path.join(self.tmp, "def.rive")
        dst = os.path.join(self.tmp, "out", "def.rive")
        with open(src, "w") as fh:
            fh.write("! var name = Bot\n> begin\n+ request\n- {ok}\n< begin\n")
        tx = _fake_translator({})
        _translate_rive_file(src, dst, tx, "pt")
        with open(dst) as fh:
            content = fh.read()
        assert "! var name = Bot" in content
        assert "> begin" in content
        assert "< begin" in content


# ---------------------------------------------------------------------------
# RiveScriptChatEngine — defaults
# ---------------------------------------------------------------------------

class TestRiveScriptDefaultBehavior:
    def test_is_chat_engine(self):
        e = RiveScriptChatEngine()
        assert isinstance(e, ChatEngine)

    def test_enable_tx_default_off(self):
        e = RiveScriptChatEngine()
        assert e.translate is False

    def test_translator_none_when_disabled(self):
        e = RiveScriptChatEngine()
        assert e._get_translator() is None

    def test_english_answer(self):
        e = RiveScriptChatEngine()
        r = e.continue_chat([AgentMessage(role=MessageRole.USER, content="hello")])
        assert isinstance(r, AgentMessage)
        assert r.content  # non-empty


# ---------------------------------------------------------------------------
# RiveScriptChatEngine — enable_tx on with mock translator
# ---------------------------------------------------------------------------

class TestBrainTranslationWithMock:
    """Verify that requesting a lang with no bundled brain + enable_tx=True
    results in a translated brain being built and cached."""

    def setup_method(self):
        self.tmp_xdg = tempfile.mkdtemp()
        # Patch XDG_PATH so we don't pollute the real user data dir.
        self._xdg_patcher = patch(
            "ovos_solver_rivescript_plugin.RivescriptBot.XDG_PATH",
            self.tmp_xdg,
        )
        self._xdg_patcher.start()

    def teardown_method(self):
        self._xdg_patcher.stop()
        shutil.rmtree(self.tmp_xdg, ignore_errors=True)

    def _make_engine_with_mock_tx(self, lang="pt-pt"):
        """Instantiate RiveScriptChatEngine with enable_tx=True and a mock translator."""
        tx = _fake_translator({})

        engine = RiveScriptChatEngine.__new__(RiveScriptChatEngine)
        # Bypass normal __init__; set attributes manually to inject mock.
        from ovos_plugin_manager.templates.agents import ChatEngine as CE
        CE.__init__(engine, {"lang": lang, "enable_tx": True})
        engine.translate = True
        engine.translator = tx
        engine._translator_loaded = True
        return engine, tx

    def test_translated_brain_dir_created(self):
        lang = "pt-pt"
        engine, tx = self._make_engine_with_mock_tx(lang)

        tx_dir = engine._build_translated_brain(lang, tx)
        assert tx_dir is not None
        assert os.path.isdir(tx_dir), f"Expected translated brain dir at {tx_dir}"
        rive_files = [f for f in os.listdir(tx_dir) if f.endswith(".rive")]
        assert rive_files, "No .rive files in translated brain dir"

    def test_cached_brain_reused(self):
        lang = "pt-pt"
        engine, tx = self._make_engine_with_mock_tx(lang)

        engine._build_translated_brain(lang, tx)
        call_count_after_first = tx.translate.call_count

        engine._build_translated_brain(lang, tx)
        # Second call must not invoke the translator again (cache hit).
        assert tx.translate.call_count == call_count_after_first

    def test_no_translator_falls_back(self):
        """If _get_translator() returns None, _resolve_brain_lang falls back to en-us."""
        engine = RiveScriptChatEngine.__new__(RiveScriptChatEngine)
        from ovos_plugin_manager.templates.agents import ChatEngine as CE
        CE.__init__(engine, {"lang": "pt-pt", "enable_tx": True})
        engine.translate = True
        engine.translator = None
        engine._translator_loaded = True  # already tried, got None

        result = engine._resolve_brain_lang("pt-pt")
        assert result == "en-us"
