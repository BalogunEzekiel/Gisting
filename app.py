import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode, RTCConfiguration
import speech_recognition as sr
from utils.translator import translate_text, generate_tts_audio
import tempfile
import os
import av
import queue
import numpy as np
import wave

# ===== Page Setup =====
st.set_page_config(page_title="🎙️ Gisting", layout="centered")

# Mobile-friendly padding + reload on JS import fail
st.markdown("""
<style>
@media (max-width: 600px) {
    .block-container {
        padding: 1rem 0.5rem !important;
    }
}
</style>
<script>
window.addEventListener("error", function(e) {
    if (e.message && e.message.includes("Failed to fetch dynamically imported module")) {
        window.location.reload();
    }
});
</script>
""", unsafe_allow_html=True)

# Logo & Title
st.image("assets/gistinglogo.png", width=150)
st.subheader("Real-Time Voice-to-Voice Translator")

# ===== Language Selection =====
languages = {
    "English": "en", "French": "fr", "Spanish": "es", "German": "de",
    "Hindi": "hi", "Tamil": "ta", "Telugu": "te", "Japanese": "ja",
    "Russian": "ru", "Yoruba": "yo", "Igbo": "ig", "Chinese": "zh-cn",
    "Swahili": "sw"
}

source_lang = st.selectbox("🎤 Select Spoken Language", options=list(languages.keys()))
target_lang = st.selectbox("🗣️ Translate To", options=list(languages.keys()), index=1)

st.markdown("💡 Speak clearly into your microphone...")

# ===== TURN/STUN Config =====
rtc_configuration = RTCConfiguration(
    {
        "iceServers": [
            {"urls": [
                "stun:stun.l.google.com:19302",
                "stun:stun1.l.google.com:19302",
                "stun:stun2.l.google.com:19302"
            ]},
            {
                "urls": [
                    "turn:global.xirsys.net:3478?transport=udp",
                    "turn:global.xirsys.net:3478?transport=tcp"
                ],
                "username": "ezekiel4true",
                "credential": "f0592ae8-73e2-11f0-a6bd-0242ac130002"
            }
        ]
    }
)

# ===== Audio Processor =====
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.result_queue = queue.Queue()

    def recv(self, frame: av.AudioFrame):
        audio_np = frame.to_ndarray()
        sample_rate = frame.sample_rate
        channels = frame.layout.channels

        # Stereo → Mono
        if channels > 1:
            audio_np = np.mean(audio_np, axis=1)

        # Float32 → int16 PCM
        audio_int16 = np.int16(audio_np * 32767)

        # Save WAV
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            with wave.open(f, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            audio_path = f.name

        # Speech recognition
        try:
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=languages[source_lang])
                self.result_queue.put(text)
        except Exception:
            self.result_queue.put("[Could not transcribe speech]")
        finally:
            os.remove(audio_path)

        return frame

# ===== Session State =====
if "transcribed" not in st.session_state:
    st.session_state.transcribed = ""

# ===== WebRTC Stream =====
webrtc_ctx = webrtc_streamer(
    key="voice-translator",
    mode=WebRtcMode.SENDRECV,
    audio_processor_factory=AudioProcessor,
    rtc_configuration=rtc_configuration,
    media_stream_constraints={"audio": True, "video": False},
    async_processing=True
)

# Optional: Show ICE state if available
if webrtc_ctx and hasattr(webrtc_ctx, "pc") and webrtc_ctx.pc:
    st.caption(f"ICE Connection State: {webrtc_ctx.pc.iceConnectionState}")

# ===== Retrieve Transcription =====
if webrtc_ctx and webrtc_ctx.state.playing and webrtc_ctx.audio_processor:
    try:
        result_text = webrtc_ctx.audio_processor.result_queue.get(timeout=1)
        if result_text and result_text != st.session_state.transcribed:
            st.session_state.transcribed = result_text
    except queue.Empty:
        pass

# ===== Display Results (Mobile-friendly) =====
if st.session_state.transcribed:
    with st.container():
        st.markdown("### ✏️ Transcribed Text")
        st.markdown(f"<p style='font-size:18px;'>{st.session_state.transcribed}</p>", unsafe_allow_html=True)

        target_code = languages[target_lang]
        translated = translate_text(
            st.session_state.transcribed,
            src_lang=languages[source_lang],
            target_lang=target_code
        )

        st.markdown("### 🌍 Translated Text")
        st.markdown(f"<p style='font-size:20px; color:green;'><b>{translated}</b></p>", unsafe_allow_html=True)

        audio_file = generate_tts_audio(translated, lang_code=target_code)
        if audio_file:
            st.markdown("### 🔊 Translated Audio")
            with open(audio_file, "rb") as f:
                st.audio(f.read(), format="audio/mp3")
            os.remove(audio_file)
        else:
            st.warning(f"Speech not supported for language: {target_lang}")
