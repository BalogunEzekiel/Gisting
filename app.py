# app.py

import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode, RTCConfiguration
import speech_recognition as sr
from utils.translator import translate_text, generate_tts_audio
import tempfile
import os
import av

# Page setup
st.set_page_config(page_title="🎙️ Gisting", layout="centered")

# Show logo and title
st.image("assets/gistinglogo.png", width=150)
st.subheader("Real-Time Voice-to-Voice Translator")

# Language dictionary (Swahili included)
languages = {
    "English": "en", "French": "fr", "Spanish": "es", "German": "de", 
    "Hindi": "hi", "Tamil": "ta", "Telugu": "te", "Japanese": "ja", 
    "Russian": "ru", "Yoruba": "yo", "Igbo": "ig", "Chinese": "zh-cn",
    "Swahili": "sw"
}

# Language selection
source_lang = st.selectbox("🎤 Select Spoken Language", options=list(languages.keys()))
target_lang = st.selectbox("🗣️ Translate To", options=list(languages.keys()), index=1)

st.markdown("💡 Speak clearly into your microphone...")

# TURN/STUN Configuration
rtc_configuration = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": ["turn:openrelay.metered.ca:80", "turn:openrelay.metered.ca:443"],
                "username": "openrelayproject",
                "credential": "openrelayproject"
            }
        ]
    }
)

# Audio processor class
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def recv(self, frame: av.AudioFrame):
        audio = frame.to_ndarray().flatten().astype('float32').tobytes()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio)
            f.flush()
            audio_path = f.name

        try:
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=languages[source_lang])
                st.session_state.transcribed = text
        except Exception as e:
            st.session_state.transcribed = "[Could not transcribe speech]"
        finally:
            os.remove(audio_path)

        return frame

# Initialize session state
if 'transcribed' not in st.session_state:
    st.session_state.transcribed = ""

# WebRTC audio stream
webrtc_streamer(
    key="voice-translator",
    mode=WebRtcMode.SENDRECV,
    audio_processor_factory=AudioProcessor,
    rtc_configuration=rtc_configuration,
    media_stream_constraints={"audio": True, "video": False}
)

# Display transcribed and translated output
if st.session_state.transcribed:
    st.markdown("### ✏️ Transcribed Text")
    st.write(st.session_state.transcribed)

    target_code = languages[target_lang]
    translated = translate_text(
        st.session_state.transcribed,
        src_lang=languages[source_lang],
        target_lang=target_code
    )

    st.markdown("### 🌍 Translated Text")
    st.success(translated)

    audio_file = generate_tts_audio(translated, lang_code=target_code)
    if audio_file:
        st.markdown("### 🔊 Translated Audio")
        with open(audio_file, "rb") as f:
            st.audio(f.read(), format="audio/mp3")
        os.remove(audio_file)
    else:
        st.warning(f"Speech not supported for language: {target_lang}")
