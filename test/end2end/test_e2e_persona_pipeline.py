"""Full-pipeline end-to-end test for ovos-solver-plugin-rivescript using ovoscope.

Proves:
  1. An utterance flows through the real OVOS intent pipeline, hits the
     persona pipeline plugin, and produces a ``speak`` message with
     non-empty text (the RiveScript persona answered).
  2. Per-session memory is recorded: the live PersonaService accumulates
     USER + ASSISTANT turns keyed by session_id, and an unknown session
     has no history.

No network access, no keys.  The RiveScript engine uses the bundled
``brain/en-us/`` directory shipped with the plugin — completely offline.
"""
import json
import os
import tempfile

import pytest

ovoscope = pytest.importorskip("ovoscope")
ovos_persona = pytest.importorskip("ovos_persona")

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session, SessionManager

from ovoscope import (
    PERSONA_PIPELINE,
    CaptureSession,
    get_minicroft,
    is_pipeline_available,
)

if not is_pipeline_available(PERSONA_PIPELINE):
    pytest.skip("ovos-persona-pipeline-plugin not installed", allow_module_level=True)

# ---------------------------------------------------------------------------
# Persona definition — uses bundled brain, no extra config needed
# ---------------------------------------------------------------------------

PERSONA_NAME = "RiveBot"

# The utterance the bundled brain reliably answers
GREETING_UTTERANCE = "hello"


def _make_personas_dir() -> str:
    """Write a minimal RiveScript persona JSON into a temp directory."""
    tmpdir = tempfile.mkdtemp()
    persona = {
        "name": PERSONA_NAME,
        "handlers": ["ovos-solver-rivescript-plugin"],
        "ovos-solver-rivescript-plugin": {
            "lang": "en-us",
        },
    }
    with open(os.path.join(tmpdir, f"{PERSONA_NAME}.json"), "w") as fh:
        json.dump(persona, fh)
    return tmpdir


# ---------------------------------------------------------------------------
# Module-level MiniCroft (shared across tests for speed)
# ---------------------------------------------------------------------------

PERSONAS_PATH = _make_personas_dir()

PIPELINE_CONFIG = {
    "persona": {
        "personas_path": PERSONAS_PATH,
        "default_persona": PERSONA_NAME,
        "short-term-memory": True,
        "handle_fallback": True,
        "ignore_plugin_personas": True,
    }
}

TEST_PIPELINE = [
    "ovos-persona-pipeline-plugin-high",
    "ovos-persona-pipeline-plugin-low",
]


@pytest.fixture(scope="module")
def mc():
    """Shared MiniCroft instance with the RiveBot persona."""
    croft = get_minicroft(
        skill_ids=[],
        default_pipeline=TEST_PIPELINE,
        pipeline_config=PIPELINE_CONFIG,
    )
    yield croft
    croft.stop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utterance_msg(utterance: str, sess: Session) -> Message:
    return Message(
        "recognizer_loop:utterance",
        {"utterances": [utterance], "lang": sess.lang},
        {"session": sess.serialize()},
    )


def _drive_utterance(croft, sess: Session, utterance: str, timeout: int = 30):
    cap = CaptureSession(
        croft,
        eof_msgs=["ovos.utterance.handled", "ovos.utterance.cancelled"],
    )
    cap.capture(_utterance_msg(utterance, sess), timeout=timeout)
    return cap.finish()


def _get_persona_service(croft):
    return croft.intents.pipeline_plugins["ovos-persona-pipeline-plugin"]


# ---------------------------------------------------------------------------
# Test 1: persona speaks through the full pipeline
# ---------------------------------------------------------------------------

class TestRivescriptPersonaSpeaksThroughPipeline:
    """An utterance must traverse the full OVOS intent pipeline and produce
    a speak message with non-empty utterance text from the RiveScript engine."""

    def test_pipeline_produces_speak(self, mc):
        sess = Session(session_id="rive-e2e-speak-test")
        SessionManager.sessions[sess.session_id] = sess

        messages = _drive_utterance(mc, sess, GREETING_UTTERANCE, timeout=30)

        msg_types = [m.msg_type for m in messages]
        speak_msgs = [m for m in messages if m.msg_type == "speak"]

        assert speak_msgs, (
            f"Expected at least one 'speak' message; got msg_types: {msg_types}"
        )
        spoken = speak_msgs[0].data.get("utterance", "")
        assert spoken.strip(), (
            f"'speak' message had an empty utterance; data={speak_msgs[0].data}"
        )

    def test_speak_message_non_empty_on_different_utterance(self, mc):
        sess = Session(session_id="rive-e2e-speak-nonempty")
        SessionManager.sessions[sess.session_id] = sess

        messages = _drive_utterance(mc, sess, "what is your name", timeout=30)

        for msg in messages:
            if msg.msg_type == "speak":
                assert msg.data.get("utterance", "").strip(), (
                    f"speak message has empty utterance: {msg.data}"
                )
                return

        pytest.fail(
            f"No 'speak' message found in pipeline output. "
            f"Message types received: {[m.msg_type for m in messages]}"
        )


# ---------------------------------------------------------------------------
# Test 2: per-session memory is recorded
# ---------------------------------------------------------------------------

class TestRivescriptPerSessionMemory:
    """PersonaService records USER+ASSISTANT turns per session_id.

    The live PersonaService is obtained from the MiniCroft pipeline registry
    (mc.intents.pipeline_plugins["ovos-persona-pipeline-plugin"]).
    """

    def test_user_turn_recorded_in_memory(self, mc):
        svc = _get_persona_service(mc)
        sess = Session(session_id="rive-e2e-mem-user")
        SessionManager.sessions[sess.session_id] = sess

        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None, f"Persona '{PERSONA_NAME}' not loaded"
        assert persona.memory is not None, "Persona must have short-term memory enabled"

        _drive_utterance(mc, sess, GREETING_UTTERANCE, timeout=30)

        history = persona.memory.get_history(sess.session_id)
        contents = [m.content for m in history]
        assert any(GREETING_UTTERANCE in c for c in contents), (
            f"User utterance not found in memory for session {sess.session_id}. "
            f"History: {contents}"
        )

    def test_assistant_response_recorded_in_memory(self, mc):
        from ovos_plugin_manager.templates.agents import MessageRole

        svc = _get_persona_service(mc)
        sess = Session(session_id="rive-e2e-mem-assistant")
        SessionManager.sessions[sess.session_id] = sess

        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None
        assert persona.memory is not None

        _drive_utterance(mc, sess, GREETING_UTTERANCE, timeout=30)

        history = persona.memory.get_history(sess.session_id)
        roles = [m.role for m in history]
        assert MessageRole.ASSISTANT in roles, (
            f"No ASSISTANT turn recorded in memory. History roles: {roles}"
        )

    def test_unknown_session_has_empty_history(self, mc):
        svc = _get_persona_service(mc)
        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None
        assert persona.memory is not None

        sess = Session(session_id="rive-e2e-mem-known")
        SessionManager.sessions[sess.session_id] = sess
        _drive_utterance(mc, sess, GREETING_UTTERANCE, timeout=30)

        unknown_history = persona.memory.get_history("session-that-never-existed-rive")
        assert unknown_history == [], (
            f"Expected empty history for unknown session, got: {unknown_history}"
        )

    def test_same_session_accumulates_turns(self, mc):
        svc = _get_persona_service(mc)
        sess = Session(session_id="rive-e2e-mem-accumulate")
        SessionManager.sessions[sess.session_id] = sess

        persona = svc.personas.get(PERSONA_NAME)
        assert persona is not None
        assert persona.memory is not None
        persona.memory.session2history.pop(sess.session_id, None)

        _drive_utterance(mc, sess, GREETING_UTTERANCE, timeout=30)
        _drive_utterance(mc, sess, "what is your name", timeout=30)

        history = persona.memory.get_history(sess.session_id)
        assert len(history) >= 2, (
            f"Expected at least 2 history entries after two turns, got {len(history)}: "
            f"{[m.content for m in history]}"
        )
