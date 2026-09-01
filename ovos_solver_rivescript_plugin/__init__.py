import os
from datetime import date
from os.path import dirname, isdir
from typing import List, Optional

from ovos_plugin_manager.templates.solvers import QuestionSolver
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from rivescript import RiveScript

try:
    from ovos_plugin_manager.templates.agents import ChatEngine, AgentMessage, MessageRole
except ImportError:
    # ovos-plugin-manager < 2.2.3a1 does not ship the agents module yet.
    # The legacy QuestionSolver below still works without it; only the
    # ChatEngine registration is unavailable on such an old install.
    ChatEngine = object
    AgentMessage = None
    MessageRole = None


class RivescriptBot:
    XDG_PATH = f"{xdg_data_home()}/rivescript"
    os.makedirs(XDG_PATH, exist_ok=True)

    # Default bot identity reflects RiveScript itself, not the upstream demo
    # personality bundled in brain/en-us/begin.rive ("Aiden" from Detroit,
    # Michigan - sample-brain placeholders, not creator-reflective) and not
    # the Mycroft project either. RiveScript was created by Noah
    # Petherbridge and first released in 2005 (originally in Perl); see
    # https://www.rivescript.com/about and https://www.rivescript.com/history
    # There is no sourced hometown or birthday for Petherbridge, so location/
    # city name RiveScript's own documented origin instead of the person's:
    # it grew out of Chatbot::Alpha and was first written in Perl, published
    # under its own root namespace on CPAN. https://www.rivescript.com/history
    DEFAULT_NAME = "RiveScript"
    RIVESCRIPT_BIRTH_YEAR = 2005
    DEFAULT_LOCATION = "CPAN"
    DEFAULT_CITY = "the Perl programming language"
    DEFAULT_MASTER = "Noah Petherbridge"
    DEFAULT_WEBSITE = "rivescript.com"

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
        if "sex" not in self.settings:
            self.settings["sex"] = "undefined"
        if "master" not in self.settings:
            self.settings["master"] = self.DEFAULT_MASTER
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
            self.settings["website"] = self.DEFAULT_WEBSITE
        if "pet" not in self.settings:
            self.settings["pet"] = "bugs"
        if "interests" not in self.settings:
            self.settings["interests"] = "I am interested in all kinds of " \
                                         "things. We can talk about anything."
        if "location" not in self.settings:
            self.settings["location"] = self.DEFAULT_LOCATION
        if "city" not in self.settings:
            self.settings["city"] = self.DEFAULT_CITY

        self.rs.load_directory(self.brain_path)
        self.rs.sort_replies()
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
        self.rs.set_variable("name", self.settings.get("name", self.DEFAULT_NAME))
        self.rs.set_variable("location", self.settings["location"])
        self.rs.set_variable("city", self.settings["city"])

        try:
            birth_year = int(self.settings.get("birth_year", self.RIVESCRIPT_BIRTH_YEAR))
        except (TypeError, ValueError) as e:
            LOG.warning(f"Invalid birth_year in config ({e}); "
                        f"falling back to {self.RIVESCRIPT_BIRTH_YEAR}")
            birth_year = self.RIVESCRIPT_BIRTH_YEAR
        age = self.settings.get("age", str(date.today().year - birth_year))
        self.rs.set_variable("age", str(age))

    def ask_brain(self, utterance):
        try:
            return self.rs.reply("human", utterance)
        except Exception as e:
            LOG.error(e)


class RivescriptSolver(QuestionSolver):
    def __init__(self, config=None):
        config = config or {"lang": "en-us"}
        lang = config.get("lang") or "en-us"
        if lang != "en-us" and lang not in os.listdir(RivescriptBot.XDG_PATH):
            config["lang"] = lang = "en-us"
        super().__init__(config, internal_lang=lang, enable_tx=True, priority=96)
        self.brain = RivescriptBot(lang, self.config)
        self.brain.load_brain()

    def get_spoken_answer(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None) -> Optional[str]:
        """
        Obtain the spoken answer for a given query.

        Args:
            query (str): The query text.
            lang (Optional[str]): Optional language code. Defaults to None.
            units (Optional[str]): Optional units for the query. Defaults to None.

        Returns:
            str: The spoken answer as a text response.
        """
        return self.brain.ask_brain(query)


class RivescriptChatEngine(ChatEngine):
    """RiveScript chatbot exposed as a modern ChatEngine agent plugin.

    RiveScript is a pattern-matching chatbot: it has no notion of tool
    calling, so ``tools`` is accepted (callers pass it by keyword) and
    ignored, and ``supports_tools`` stays at the base default of False.
    """

    def __init__(self, config=None):
        config = config or {"lang": "en-us"}
        lang = config.get("lang") or "en-us"
        if lang != "en-us" and lang not in os.listdir(RivescriptBot.XDG_PATH):
            config["lang"] = lang = "en-us"
        super().__init__(config)
        self.brain = RivescriptBot(lang, self.config)
        self.brain.load_brain()

    def continue_chat(self, messages: List["AgentMessage"],
                      session_id: str = "default",
                      lang: Optional[str] = None,
                      units: Optional[str] = None,
                      tools=None) -> "AgentMessage":
        """
        Answer the latest user message via the RiveScript brain.

        RiveScript itself has no concept of chat history beyond the single
        reply it is asked for, so only the most recent user message is used;
        earlier turns in ``messages`` are ignored, same as upstream RiveScript
        usage elsewhere in this plugin.
        """
        query = next((m.content for m in reversed(messages)
                      if m.role == MessageRole.USER), "")
        if not query:
            return AgentMessage(role=MessageRole.ASSISTANT, content="")
        answer = self.brain.ask_brain(query) or ""
        return AgentMessage(role=MessageRole.ASSISTANT, content=answer)


if __name__ == "__main__":
    bot = RivescriptSolver()
    print(bot.get_spoken_answer("hello!"))
    print(bot.spoken_answer("Qual é a tua comida favorita?", lang="pt-pt"))

    chat = RivescriptChatEngine()
    reply = chat.continue_chat([AgentMessage(role=MessageRole.USER, content="hello!")])
    print(reply.content)
