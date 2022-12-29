### Voice Actor

Perform actions using your voice! In the style of Siri, Alexa, etc.

Select a wakeword and write a small function like:

```python
def detect_wakeword(text):
    # Add common misunderstandings here for better detection
    return any(text.contains(word) for word in ['Actor'])
```

And run on a linux computer (I've only tested linux, it probably works on others?) like:

```python
from voice_actor import run_voice

def commands(result):
   # Do anything you want here!
   print(result)


def detect_wakeword(text):
    # Add common misunderstandings here for better detection
    return any(text.contains(word) for word in ['Actor'])


r, p = run_voice(commands, detect_wakeword)
p.join()
```
