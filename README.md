# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/robot.svg' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Rivescript Chatbot

This plugin is a question solver that answers with a [Rivescript](https://www.rivescript.com/) chatbot. It uses the [Alice chatbot](https://www.chatbots.org/chatbot/a.l.i.c.e/) brain to answer phrases that no other skill handles, so almost every input gets some response. Answers can be casual and a bit sassy.

## Examples

* "Do you like ice cream"
* "Do you like dogs"
* "I have a jump rope"

## Usage

The plugin exposes a spoken-answers API with a Rivescript backend.

```python
from ovos_solver_rivescript_plugin import RivescriptSolver

d = RivescriptSolver()
sentence = d.spoken_answer("hello")
print(sentence)
# Hi there!

sentence = d.spoken_answer("Do you like ice cream", {"lang": "pt-pt"})
print(sentence)
# O que queres mesmo saber?
```

## Related projects

* [OpenVoiceOS/ovos-plugin-manager](https://github.com/OpenVoiceOS/ovos-plugin-manager): loads and manages solver plugins like this one.
* [OpenVoiceOS/ovos-persona-server](https://github.com/OpenVoiceOS/ovos-persona-server): runs solver plugins as chat personas.
