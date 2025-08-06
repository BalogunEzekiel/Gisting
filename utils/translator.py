# utils/translator.py

from deep_translator import GoogleTranslator
from gtts import gTTS
from gtts.lang import tts_langs
import os
import uuid

tts_supported = tts_langs().keys()

def translate_text(text, src_lang='auto', target_lang='en'):
    try:
        translated = GoogleTranslator(source=src_lang, target=target_lang).translate(text)
        return translated
    except Exception as e:
        return f"[Translation Error: {str(e)}]"

def generate_tts_audio(text, lang_code):
    try:
        if lang_code in tts_supported:
            tts = gTTS(text, lang=lang_code)
            filename = f"{uuid.uuid4().hex}.mp3"
            tts.save(filename)
            return filename
        else:
            return None
    except Exception as e:
        return None
