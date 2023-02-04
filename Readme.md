# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/robot.svg' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Rivescript Chatbot
 
Give Mycroft some sass with Rivescript!

Leverages the [Alice chatbot](https://www.chatbots.org/chatbot/a.l.i.c.e/) to create some fun interactions.  Phrases not explicitly handled by other skills will be run by the chatbot, so nearly every interaction will have _some_ response.  But be warned, Mycroft might become a bit obnoxious...

## Examples 
* "Do you like ice cream"
* "Do you like dogs"
* "I have a jump rope"


## Usage

Spoken answers api with a Rivescript backend

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
