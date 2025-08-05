import os
from langchain_community.document_loaders.parsers.audio import OpenAIWhisperParser
from langchain_community.document_loaders.generic import GenericLoader
from dotenv import load_dotenv, find_dotenv

# Load env variables
load_dotenv(find_dotenv())


class _Transcriber:
    """
    Singleton utility to transcribe audio files using OpenAI's Whisper model.
    """

    def __init__(self, lang="fr", model_name="whisper-1"):
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("Missing OPENAI_API_KEY environment variable.")

        self.__parser = OpenAIWhisperParser(
            api_key=os.getenv("OPENAI_API_KEY"),
            chunk_duration_threshold=0.7,
            language=lang,
            response_format="text",
            temperature=0.0,
            model=model_name,
        )

    def get_transcription(self, audio_file_path: str):
        if not os.path.isfile(audio_file_path):
            raise FileNotFoundError(f"The file {audio_file_path} does not exist.")

        if not audio_file_path.lower().endswith((".mp3", ".wav", ".m4a")):
            raise ValueError("Supported formats are: .mp3, .wav, .m4a.")

        loader = GenericLoader.from_filesystem(
            path=audio_file_path,
            suffixes=[".mp3", ".wav", ".m4a"],
            show_progress=False,
            parser=self.__parser,
        )

        documents = loader.load()

        if not documents:
            raise ValueError("No documents were loaded from the audio file.")

        return " ".join(doc.page_content for doc in documents)


# Singleton instance
transcriber = _Transcriber()


def transcribe_audio(file_path: str):
    return transcriber.get_transcription(file_path)
