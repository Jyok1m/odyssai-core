# 🚀 Odyssai Core

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/charliermarsh/ruff)

**Odyssai Core** is the central AI module of the Odyssai project, an intelligent procedural RPG assistant that combines AI content generation, voice synthesis, and speech recognition to create immersive and interactive role-playing experiences.

## ✨ Features

### 🎮 Procedural Generation
- **World Creation**: Automatic generation of fantasy and science-fiction universes
- **Dynamic Characters**: Creation of characters with unique personalities, stories, and motivations
- **Living Lore**: Progressive development of world history and mythology
- **Narrative Events**: Contextual generation of situations and challenges

### 🎵 Advanced Audio Interface
- **Voice Synthesis**: Text-to-Speech with Google Cloud TTS
- **Speech Recognition**: Audio transcription via OpenAI Whisper
- **Interactive Voice Mode**: Fully voice-based interaction for total immersion
- **Multi-format Support**: Compatible with MP3, WAV, M4A

### 🧠 AI and Machine Learning
- **LangChain + LangGraph**: Advanced AI workflow orchestration
- **OpenAI GPT**: High-quality narrative content generation
- **ChromaDB**: Vector database for persistence and semantic search
- **Embeddings**: Intelligent contextual search within the game universe

### 📊 Modular Architecture
- **Configurable Workflows**: Flexible and extensible processing pipelines
- **Persistent State**: Automatic saving of progress and context
- **Typed Schemas**: Robust data structure with Pydantic validation
- **Traceability**: Monitoring and debugging with LangSmith

## 🛠️ Installation

### Prerequisites
- Python 3.12+
- Conda (recommended) or pip
- API Keys: OpenAI, Google Cloud TTS, ChromaDB Cloud

### Installation via Conda (Recommended)

```bash
# Clone the repository
git clone https://github.com/Jyok1m/odyssai-core.git
cd odyssai-core

# Create conda environment
conda env create -f environment.yml
conda activate odyssai

# Install package in development mode
pip install -e .
```

### Installation via pip

```bash
# Clone the repository
git clone https://github.com/Jyok1m/odyssai-core.git
cd odyssai-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
```

### Environment Variables Configuration

Create a `.env` file at the project root:

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS=path/to/google_tts.json

# ChromaDB Cloud
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_tenant
CHROMA_DATABASE=your_database

# LangSmith (optional, for monitoring)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=odyssai-core

# Other APIs (optional)
HF_API_KEY=your_huggingface_api_key
PINECONE_API_KEY=your_pinecone_api_key
SERPAPI_API_KEY=your_serpapi_api_key
```

## 🚀 Usage

### Running the Application

```bash
# Via installed script
odyssai

# Or directly via Python
python -m odyssai_core
```

### Programmatic Usage Example

```python
from odyssai_core.workflows.main_graph import main_graph

# Initial configuration
initial_state = {}

# Launch the workflow
result = main_graph.invoke(
    initial_state, 
    config={"recursion_limit": 9999}
)
```

### Available Modules

```python
# Audio transcription
from odyssai_core.utils.whisper import transcribe_audio
audio_text = transcribe_audio("path/to/audio.mp3")

# Voice synthesis
from odyssai_core.utils.google_tts import text_to_speech
audio_path = text_to_speech("Hello, adventurer!")

# Recording session
from odyssai_core.utils.audio_session import recorder
recorder.start()
# ... recording ...
audio_file = recorder.stop()
```

## 🏗️ Architecture

### Project Structure

```
odyssai-core/
├── src/odyssai_core/
│   ├── __init__.py
│   ├── __main__.py              # Main entry point
│   ├── config/
│   │   ├── paths.py             # Path configuration
│   │   └── settings.py          # Environment variables
│   ├── constants/
│   │   ├── interaction_cues.py  # Interface messages
│   │   └── llm_models.py        # Model configuration
│   ├── utils/
│   │   ├── audio_session.py     # Audio session management
│   │   ├── google_tts.py        # Google voice synthesis
│   │   ├── prompt_truncation.py # Prompt optimization
│   │   └── whisper.py           # Whisper transcription
│   └── workflows/
│       └── main_graph.py        # Main LangGraph workflow
├── environment.yml              # Conda environment
├── pyproject.toml              # Project configuration
└── README.md                   # This file
```

### Main Workflow

The system uses a LangGraph workflow graph that orchestrates:

1. **Initialization**: World configuration and input validation
2. **World Creation**: Basic universe generation
3. **Lore Generation**: Story and mythology enrichment
4. **Character Creation**: Protagonist development
5. **Interactive Gameplay**: Game loop with dynamic responses
6. **Persistence**: Saving to ChromaDB

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the project
2. **Create** a feature branch (`git checkout -b feature/new-feature`)
3. **Commit** your changes (`git commit -am 'Add new feature'`)
4. **Push** to the branch (`git push origin feature/new-feature`)
5. **Open** a Pull Request

### Code Conventions

- Follow **Ruff** style for formatting
- Use **type hints** for all functions
- Write **docstrings** for public modules
- Add **tests** for new features

## 🔍 Troubleshooting

### Common Issues

**OpenAI Authentication Error**
```bash
# Check API key
echo $OPENAI_API_KEY
```

**Google TTS Issue**
```bash
# Check credentials file
echo $GOOGLE_APPLICATION_CREDENTIALS
```

**ChromaDB Not Accessible**
```bash
# Test connection
python -c "import chromadb; print('ChromaDB OK')"
```

### Audio Support

Make sure you have audio codecs installed:

```bash
# macOS
brew install portaudio ffmpeg

# Ubuntu/Debian
sudo apt-get install portaudio19-dev ffmpeg

# Windows
# Install via conda recommended
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT and Whisper models
- **Google Cloud** for Text-to-Speech services
- **LangChain** for the AI orchestration framework
- **ChromaDB** for the vector database
- **Python Community** for the fantastic ecosystem

---

**Developed with ❤️ by [Joachim Jasmin](mailto:joachim.jasmin-dev@proton.me)**