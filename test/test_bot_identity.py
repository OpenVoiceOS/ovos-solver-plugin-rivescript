"""Regression tests: bot identity must reflect the RiveScript lineage, not
Mycroft or the upstream demo persona, and must be configurable.

This plugin is not Mycroft and OVOS does not carry Mycroft attribution, so
the RiveScript identity variables must never default to Mycroft's identity,
and must never default to the upstream RiveScript demo personality bundled
in brain/en-us/begin.rive either ("Aiden" from Detroit, Michigan). Every
identity variable must be overridable via config.
"""
import unittest
from datetime import date

from ovos_plugin_manager.templates.agents import AgentMessage, MessageRole

from ovos_solver_rivescript_plugin import RivescriptBot, RivescriptChatEngine


class TestBotIdentity(unittest.TestCase):
    def test_default_name_is_not_mycroft(self):
        bot = RivescriptBot()
        bot.load_brain()
        name = bot.rs.get_variable("name")
        self.assertNotEqual(name.lower(), "mycroft")
        self.assertEqual(name, RivescriptBot.DEFAULT_NAME)

    def test_default_age_derives_from_rivescript_birth_year_not_mycroft(self):
        bot = RivescriptBot()
        bot.load_brain()
        expected = str(date.today().year - RivescriptBot.RIVESCRIPT_BIRTH_YEAR)
        self.assertEqual(bot.rs.get_variable("age"), expected)

    def test_default_master_is_not_mycroft_or_skynet(self):
        bot = RivescriptBot()
        bot.load_brain()
        master = bot.rs.get_variable("master")
        self.assertNotEqual(master.lower(), "mycroft")
        self.assertNotEqual(master.lower(), "skynet")
        self.assertEqual(master, RivescriptBot.DEFAULT_MASTER)

    def test_configured_name_reaches_the_answer(self):
        engine = RivescriptChatEngine({"lang": "en-us", "name": "Zorb"})
        self.assertEqual(engine.brain.rs.get_variable("name"), "Zorb")
        reply = engine.continue_chat(
            [AgentMessage(role=MessageRole.USER, content="what is your name")]
        )
        self.assertIn("zorb", reply.content.lower())

    def test_default_location_and_city_are_not_the_upstream_demo(self):
        # brain/en-us/begin.rive hardcodes "! var location = Michigan" and
        # "! var city = Detroit" (the upstream RiveScript demo persona,
        # "Aiden"). Both must be overridden, not left to leak through.
        bot = RivescriptBot()
        bot.load_brain()
        self.assertNotEqual(bot.rs.get_variable("location"), "Michigan")
        self.assertNotEqual(bot.rs.get_variable("city"), "Detroit")
        self.assertEqual(bot.rs.get_variable("location"), RivescriptBot.DEFAULT_LOCATION)
        self.assertEqual(bot.rs.get_variable("city"), RivescriptBot.DEFAULT_CITY)

    def test_default_location_and_city_name_the_language_not_the_cloud(self):
        # location/city name RiveScript's own documented origin (Perl/CPAN,
        # per https://www.rivescript.com/history), a fact about the
        # language, not a bland placeholder and not a guess about
        # Petherbridge's personal whereabouts.
        bot = RivescriptBot()
        bot.load_brain()
        self.assertEqual(bot.rs.get_variable("location"), "CPAN")
        self.assertEqual(bot.rs.get_variable("city"), "the Perl programming language")

    def test_configured_location_reaches_the_answer(self):
        engine = RivescriptChatEngine({"lang": "en-us", "location": "Lisbon"})
        reply = engine.continue_chat(
            [AgentMessage(role=MessageRole.USER, content="where are you from")]
        )
        self.assertIn("lisbon", reply.content.lower())
        self.assertNotIn("michigan", reply.content.lower())

    def test_configured_city_reaches_the_answer(self):
        engine = RivescriptChatEngine({"lang": "en-us", "city": "Lisbon"})
        reply = engine.continue_chat(
            [AgentMessage(role=MessageRole.USER, content="what city are you from")]
        )
        self.assertIn("lisbon", reply.content.lower())
        self.assertNotIn("detroit", reply.content.lower())

    def test_no_dead_birthday_constant(self):
        # DEFAULT_BIRTHDAY was removed: nothing in the bundled corpus reads
        # <bot birthday>, so a constant feeding it would reach no answer.
        self.assertFalse(hasattr(RivescriptBot, "DEFAULT_BIRTHDAY"))

    def test_invalid_birth_year_does_not_crash_construction(self):
        # A bad config value here must degrade with a warning, not raise -
        # QuestionSolversService.load_plugins has no try/except around
        # plugin construction, so an uncaught ValueError here takes down the
        # whole Persona, not just this handler.
        engine = RivescriptChatEngine({"lang": "en-us", "birth_year": "not-a-year"})
        expected = str(date.today().year - RivescriptBot.RIVESCRIPT_BIRTH_YEAR)
        self.assertEqual(engine.brain.rs.get_variable("age"), expected)


if __name__ == "__main__":
    unittest.main()
