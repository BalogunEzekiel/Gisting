import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration, AudioProcessorBase
from utils.translator import translate_text, generate_tts_audio
import av
import queue

# RTC Configuration (uses public Google STUN server)
rtc_config = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": ["turn:your.turn.server:3478"],
                "username": "your_username",
                "credential": "your_password"
            }
        ]
    }
)


# Setup audio queue
audio_queue = queue.Queue()

# Page configuration
st.set_page_config(page_title="🎙️ Gisting - Real-time Speech Translator", layout="centered")
st.title("🎙️ Gisting - Real-time Speech Translator")

st.markdown("Speak into your mic, get instant translation and audio playback in your preferred language.")

# Language settings
target_lang = st.selectbox("Select language to translate to", ["en", "fr", "de", "es", "ha", "yo", "ig"], index=0)

# Define AudioProcessor
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recognizer = None
        self.mic_ready = False

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        audio_data = frame.to_ndarray()
        audio_queue.put(audio_data)
        return frame

# WebRTC streamer
webrtc_ctx = webrtc_streamer(
    key="speech-translator",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=rtc_config,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False}
)

# Handle translation and TTS
if webrtc_ctx.state.playing:
    st.success("Microphone is live. Start speaking...")

    if not audio_queue.empty():
        st.info("Processing audio...")

        # Note: you need to convert audio_queue data to a proper format for speech recognition.
        # This placeholder can be replaced with the actual speech_recognition processing.

        try:
            import speech_recognition as sr
            import numpy as np
            import tempfile
            import wave

            recognizer = sr.Recognizer()

            # Get audio data from queue
            frames = []
            while not audio_queue.empty():
                frames.append(audio_queue.get())

            if frames:
                audio_data = np.concatenate(frames).astype(np.int16)

                # Save audio to temporary WAV file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    with wave.open(f.name, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit = 2 bytes
                        wf.setframerate(16000)  # standard sample rate
                        wf.writeframes(audio_data.tobytes())
                    temp_wav_path = f.name

                with sr.AudioFile(temp_wav_path) as source:
                    audio = recognizer.record(source)

                try:
                    # Transcribe
                    text = recognizer.recognize_google(audio)
                    st.write(f"**You said:** {text}")

                    # Translate
                    translated = translate_text(text, target_lang=target_lang)
                    st.success(f"**Translated ({target_lang}):** {translated}")

                    # TTS
                    tts_path = generate_tts_audio(translated, target_lang)
                    st.audio(tts_path, format="audio/mp3")

                except sr.UnknownValueError:
                    st.error("Could not understand the audio.")
                except sr.RequestError as e:
                    st.error(f"Could not request results; {e}")

        except Exception as e:
            st.error(f"An error occurred while processing the audio: {e}")
else:
    st.warning("Please click 'Start' to activate the microphone.")
