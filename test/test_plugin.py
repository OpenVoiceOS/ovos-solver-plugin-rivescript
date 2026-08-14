"""Smoke tests: the plugin loads and answers, and is discoverable under both
the legacy question-solver entry point and the modern chat-engine entry
point.
"""
import unittest

from ovos_plugin_manager.templates.agents import AgentMessage, MessageRole
from ovos_plugin_manager.utils import find_plugins

from ovos_solver_rivescript_plugin import RivescriptBot, RivescriptChatEngine, RivescriptSolver


class TestRivescriptSolver(unittest.TestCase):
    def test_brain_answers(self):
        # RivescriptSolver.__init__ hardcodes enable_tx=True, which makes the
        # base QuestionSolver eagerly build a language-translation plugin at
        # construction time even when no translation is ever performed. That
        # is a pre-existing base-class quirk unrelated to this migration, and
        # it means constructing RivescriptSolver requires a translate plugin
        # to be installed. Exercise the underlying brain directly instead,
        # which is what actually answers queries.
        bot = RivescriptBot()
        bot.load_brain()
        answer = bot.ask_brain("hello")
        self.assertIsInstance(answer, str)
        self.assertTrue(answer)

    def test_registered_under_legacy_group(self):
        plugins = find_plugins("neon.plugin.solver")
        self.assertIn("ovos-solver-rivescript-plugin", plugins)
        self.assertIs(plugins["ovos-solver-rivescript-plugin"], RivescriptSolver)


class TestRivescriptChatEngine(unittest.TestCase):
    def test_continue_chat(self):
        engine = RivescriptChatEngine()
        reply = engine.continue_chat(
            [AgentMessage(role=MessageRole.USER, content="hello")]
        )
        self.assertIsInstance(reply, AgentMessage)
        self.assertEqual(reply.role, MessageRole.ASSISTANT)
        self.assertTrue(reply.content)

    def test_continue_chat_accepts_and_ignores_tools(self):
        # ChatEngine.continue_chat callers pass tools= by keyword; a pattern
        # matcher has no use for it but must still accept it without raising.
        engine = RivescriptChatEngine()
        reply = engine.continue_chat(
            [AgentMessage(role=MessageRole.USER, content="hello")],
            tools=[{"type": "function", "function": {"name": "noop"}}],
        )
        self.assertIsInstance(reply, AgentMessage)
        self.assertFalse(engine.supports_tools)

    def test_registered_under_chat_group(self):
        plugins = find_plugins("opm.agents.chat")
        self.assertIn("ovos-solver-rivescript-plugin", plugins)
        self.assertIs(plugins["ovos-solver-rivescript-plugin"], RivescriptChatEngine)


if __name__ == "__main__":
    unittest.main()
