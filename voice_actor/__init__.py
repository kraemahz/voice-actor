"""Voice actor: perform actions with your voice! In the style of Siri, Alexa, etc..."""
from collections import deque
from queue import Queue, Empty
from typing import Callable
from functools import partial
from logging import debug

import threading

import numpy as np
import sounddevice as sd
import whisper


SPEECH_THRESHOLD = 0.7
RECORD_TIMEOUT = 15


def load_model_base():
    """Loads the base English whisper model, used for wakeword detection"""
    return whisper.load_model("base.en")


def load_model():
    """Loads the medium English whisper model, change this to get other languages"""
    return whisper.load_model("medium.en")


class RecordSelection(threading.Thread):
    """Continuously record from a mic and push results into two queues (short and long)"""
    fs = 16000  # Whisper only works at this sample rate! It broke when I tried others.
    channels = 1  # Number of mic directions, only works with 1
    duration = 0.5  # Seconds
    window = 2  # Seconds

    def __init__(self):
        self.queue_size = int(self.window / self.duration)
        self.running = False
        self.parse_queue = Queue()
        self.long_queue = Queue()
        self.trigger = False

        super().__init__()
        self.daemon = True

    def trigger_long(self):
        with self.long_queue.mutex:
            self.long_queue.queue.clear()
        self.trigger = True

    def stop_long(self):
        self.trigger = False

    def run(self):
        queue = deque(maxlen=self.queue_size)

        self.running = True
        while self.running:
            if self.trigger:
                if queue:
                    array = np.concatenate(list(queue))
                    self.long_queue.put(array)
                    queue.clear()
                recording = sd.rec(int(self.fs * self.window),
                                   samplerate=self.fs,
                                   channels=self.channels)
                sd.wait()
                recording = recording.reshape(recording.shape[0])
                self.long_queue.put(recording)
            else:
                recording = sd.rec(int(self.fs * self.duration),
                                   samplerate=self.fs,
                                   channels=self.channels)
                sd.wait()
                recording = recording.reshape(recording.shape[0])
                queue.append(recording)

                if len(queue) == self.queue_size:
                    array = np.concatenate(list(queue))
                    self.parse_queue.put(array)


class ParseThread(threading.Thread):
    """Parse speech with Whisper and call `command_handler` with the result if
    `detect_wakeword` returns True.
    """

    def __init__(self,
                 recording_thread: RecordSelection,
                 command_handler: Callable,
                 detect_wakeword: Callable[[str], bool],
                 use_result=False):
        self.record = recording_thread
        self.base = load_model_base()
        self.medium = load_model()
        self.running = False
        self.command = command_handler
        self.detect_wakeword = detect_wakeword
        self.use_result = use_result

        super().__init__()
        self.daemon = True

    def run(self):
        self.running = True
        while self.running:
            try:
                item = self.record.parse_queue.get(timeout=10)
            except Empty:
                continue

            result = parse_recording(self.base, item)
            if self.use_result:
                detect = self.detect_wakeword(result)
            else:
                detect = self.detect_wakeword(result.text)

            if detect:
                debug("Detected wakeword: %s", result.text)
                self.collect()

                debug("Flush queue")
                try:
                    while True:
                        self.record.parse_queue.get_nowait()
                except Empty:
                    debug("Done")
                    continue
                
    def collect(self):
        """Begin longer collection until we stop detecting voice"""
        self.record.trigger_long()
        collected = []
        while True:
            try:
                next = self.record.long_queue.get(timeout=RECORD_TIMEOUT)
            except Empty:
                debug("Empty queue")
                self.record.stop_long()
                return

            result = parse_recording(self.base, next)
            if result.no_speech_prob > SPEECH_THRESHOLD:
                debug("No further speech")
                break
            collected.append(next)

        if collected:
            array = np.concatenate(collected)
            result = parse_recording(self.medium, array)
            debug("Send command: '%s'", result.text)
            self.command(result)

        self.record.stop_long()


def run_voice(commands, wakeword_detection, use_result=False):
    """Run both threads, returning them"""
    record = RecordSelection()
    parse = ParseThread(record, commands, wakeword_detection, use_result)
    record.start()
    parse.start()
    return (record, parse)


def parse_recording(model, recording):
    """Use a whisper model to parse the recording. This is where the magic happens."""
    audio = whisper.pad_or_trim(recording)
    me = whisper.log_mel_spectrogram(audio).to(model.device)
    options = whisper.DecodingOptions(language="en")
    result = whisper.decode(model, me, options)
    return result
