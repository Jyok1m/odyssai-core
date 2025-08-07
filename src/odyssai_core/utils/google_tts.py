import tempfile
from google.cloud import texttospeech


class _Speaker:
    def __init__(
        self,
    ):
        self.__client = None
        self.language_code = "en-US"
        self.voice_name = "en-US-Wavenet-D"
        self.output_path = None

    def synthesize(self, text: str):
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string.")

        if self.__client is None:
            self.__client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        voice = texttospeech.VoiceSelectionParams(
            language_code=self.language_code, name=self.voice_name
        )
        synthesized_result = self.__client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        if not synthesized_result.audio_content:
            raise RuntimeError(
                "Failed to synthesize speech. No audio content returned."
            )

        with tempfile.NamedTemporaryFile(
            suffix=".mp3", prefix="odyssai_", delete=False
        ) as tmpfile:
            tmpfile.write(synthesized_result.audio_content)
            self.output_path = tmpfile.name

        return self.output_path


speaker = _Speaker()


def text_to_speech(text: str) -> str:
    return speaker.synthesize(text)
