import os
from datetime import date
from os.path import dirname, isdir
from typing import List, Optional

from ovos_plugin_manager.templates.agents import AgentMessage, ChatEngine, MessageRole
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from rivescript import RiveScript


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
        lang = config.get("lang") or "en-us"
        if lang != "en-us" and lang not in os.listdir(RivescriptBot.XDG_PATH):
            config["lang"] = lang = "en-us"
        super().__init__(config)
        self.brain = RivescriptBot(lang, self.config)
        self.brain.load_brain()

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
