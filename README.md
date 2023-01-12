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

def commands(results):
   # Do anything you want here! Each part of result is at most 30 seconds, due to whisper limitations
   print(' '.join(result.text for result in results])


def detect_wakeword(text):
    # Add common misunderstandings here for better detection
    return any(text.contains(word) for word in ['Actor'])


r, p = run_voice(commands, detect_wakeword)
# These threads are returned so they can be joined on or cancelled
p.join()
```

Here's a minimal example of how you might use this to use this as a speech transcriber:
```python
from voice_actor import run_voice

class FileWriter:
    def __init__(self, filename):
        self.file = open(filename, 'a')
    def write(self, results):
        text = ' '.join(result.text for result in results]
        self.file.write(text + '\n')
        self.file.flush()  # Writes will buffer in memory without this

writer = FileWriter('example.txt')
r, p = run_voice(writer.write,
                 # Custom wakeword, records if the probability of speech is >0.7
                 lambda x: x.no_speech_prob < 0.3,
                 True)
p.join()
```
