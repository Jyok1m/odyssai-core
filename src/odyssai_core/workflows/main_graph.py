# Libs
import chromadb
import ast
import textwrap
import shutil
import subprocess
import time
import threading
from uuid import uuid4
from datetime import datetime
from typing_extensions import TypedDict, Literal, NotRequired

# Langchain
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langsmith import traceable

# Modules
from odyssai_core.utils.google_tts import text_to_speech
from odyssai_core.utils.whisper import transcribe_audio
from odyssai_core.utils.audio_session import recorder
from odyssai_core.utils.prompt_truncation import truncate_structured_prompt
from odyssai_core.config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from odyssai_core.constants.llm_models import LLM_NAME, EMBEDDING_MODEL

# Static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)
TERMINAL_WIDTH = shutil.get_terminal_size((80, 20)).columns
VOICE_MODE_ENABLED = False
MAIN_TEMP = 0.7

# ------------------------------------------------------------------ #
#                                SCHEMA                              #
# ------------------------------------------------------------------ #


class StateSchema(TypedDict):
    source: Literal["cli", "api"]

    # Init Data
    world_genre: NotRequired[str]
    story_directives: NotRequired[str]
    create_new_world: NotRequired[bool]
    must_restart_init: NotRequired[bool]
    user_input: NotRequired[str]

    # World Data
    world_id: NotRequired[str]
    world_name: NotRequired[str]
    llm_generated_data: NotRequired[
        list[dict[str, str]]
    ]  # Swap data for better handling
    active_step: NotRequired[
        Literal[
            "world_creation",
            "lore_generation",
            "character_creation",
            "summary_generation",
        ]
    ]

    # Global Data
    world_context: NotRequired[str]
    lore_context: NotRequired[str]
    character_context: NotRequired[str]
    event_context: NotRequired[str]
    world_summary: NotRequired[str]

    # Gameplay Data
    ai_question: NotRequired[str]
    continue_story: NotRequired[bool]

    # Audio Data
    audio_path: NotRequired[str]

    # Character Data
    create_new_character: NotRequired[bool]
    character_id: NotRequired[str]
    character_name: NotRequired[str]
    character_gender: NotRequired[str]
    character_description: NotRequired[str]
    must_restart_character: NotRequired[bool]
    player_answer: NotRequired[str]
    immediate_events: NotRequired[str]

    # Message Classification Data
    user_message: NotRequired[str]
    classification_result: NotRequired[str]


# ------------------------------------------------------------------ #
#                       Audio Utility Functions                      #
# ------------------------------------------------------------------ #


def transcribe_audio_file(audio_path: str) -> str:
    transcript = transcribe_audio(audio_path)
    return transcript.strip()


def play_text_using_google_tts(text: str) -> None:
    audio_path = text_to_speech(text)
    subprocess.run(["afplay", audio_path])


def type_print(text: str, delay: float = 0.05, width: int = 80) -> None:
    wrapped = textwrap.fill(text, width=width)
    for char in wrapped:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def play_and_type(cue: str, width: int = 80):
    # Lance la synthèse vocale en parallèle
    tts_thread = threading.Thread(
        target=play_text_using_google_tts, args=(cue,), daemon=True
    )
    tts_thread.start()

    # Affiche le texte progressivement
    type_print(f"AI: {cue}", width=width)


# ------------------------------------------------------------------ #
#                  PLAYER INPUT (VOICE OR TEXT) UTILITY              #
# ------------------------------------------------------------------ #


def get_player_answer(cue: str, force_type: bool = False) -> str:
    print("\n")
    play_and_type(cue, width=TERMINAL_WIDTH)

    if not VOICE_MODE_ENABLED or force_type:
        return input("Type in your answer: ").strip()

    # If using voice input, run the 3-step voice pipeline manually
    input("Press Enter to record")
    print("\n")
    print("AI: I am listening...")
    recorder.start()

    input("")
    audio_path = recorder.stop()
    response = transcribe_audio_file(audio_path)
    return response


# ------------------------------------------------------------------ #
#                     WORLD GENERATION FUNCTIONS                     #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Ask player if they want to create a new world")
def ask_if_new_world(state: StateSchema) -> StateSchema:
    cue = (
        "Welcome to Odyssai. "
        "Start by answering a few questions and let's get started! "
        "Do you want to create a new world? Respond by typing 'yes' or 'no'."
    )
    response = get_player_answer(cue, force_type=True).lower()
    state["create_new_world"] = response in ["yes", "y"]
    return state


@traceable(run_type="chain", name="Ask for the name of the world")
def ask_world_name(state: StateSchema) -> StateSchema:
    if state.get("create_new_world"):
        cue = "How would you like to name your world?"
    else:
        cue = "Which existing world would you like to enter?"

    world_name = get_player_answer(cue, force_type=True)
    state["world_name"] = world_name.strip().lower()
    state["user_input"] = world_name.strip()
    return state


@traceable(run_type="chain", name="Check if world exists")
def check_world_exists(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )
    result = db_collection.get(where={"world_name": state.get("world_name", "")})
    world_exists = len(result["ids"]) > 0

    if world_exists and state.get("create_new_world"):
        cue = (
            f"The world '{state.get('world_name')}' already exists. "
            "Please restart the process and choose a different name."
        )
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_init"] = True
            return state
        else:
            raise ValueError(cue)

    elif not world_exists and not state.get("create_new_world"):
        cue = (
            f"The world '{state.get('world_name')}' does not exist. "
            "You must choose a different name or create a new world."
        )
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_init"] = True
            return state
        else:
            raise ValueError(cue)

    state["must_restart_init"] = False
    state["create_new_world"] = not world_exists
    state["world_id"] = result["ids"][0] if result["ids"] else str(uuid4())
    return state


@traceable(run_type="chain", name="Check if world exists by id")
def check_world_exists_by_id(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )
    result = db_collection.get(ids=[state.get("world_id", "")])
    world_exists = result["ids"]

    if not world_exists:
        raise ValueError("World does not exist")
    else:
        state["world_name"] = result["metadatas"][0].get("world_name", "")
        return state


@traceable(run_type="chain", name="Check if character exists by id")
def check_character_exists_by_id(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="characters",
    )
    result = db_collection.get(ids=[state.get("character_id", "")])
    character_exists = result["ids"]

    if not character_exists:
        raise ValueError("Character does not exist")
    else:
        state["character_name"] = result["metadatas"][0].get("character_name", "")
        return state


@traceable(run_type="chain", name="Ask for the genre of the world")
def ask_world_genre(state: StateSchema) -> StateSchema:
    cue = "Describe the world’s main genre. Give as much detail as you would like. "
    world_genre = get_player_answer(cue)
    state["world_genre"] = (
        world_genre.strip() if world_genre else "Choose a random genre"
    )
    return state


@traceable(run_type="chain", name="Ask for story directives")
def ask_story_directives(state: StateSchema) -> StateSchema:
    cue = "Are there particular themes or narrative threads you’d like to explore? Let your imagination guide the story’s soul."
    story_directives = get_player_answer(cue)
    state["story_directives"] = (
        story_directives.strip()
        if story_directives
        else "No specific directives provided."
    )
    return state


@traceable(run_type="chain", name="LLM Generate World Data")
def llm_generate_world_data(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = "I am generating the data for your new world. This may take a few moments, please be patient..."
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)

    state["active_step"] = "world_creation"

    prompt_template = """
    ## ROLE
    You are a world creator for a procedural RPG game.  
    You make short and vivid descriptions that help players imagine the world "{{world_name}}" (in normal case).

    ## OBJECTIVE
    Your job is to write an overview of the world "{{world_name}}".  
    The text should match the style and theme: {{world_genre}}  
    You must also follow these extra instructions: {{story_directives}}  
    Use simple words and expressions so a 15-year-old teenager can understand everything.

    ## FORMAT
    - Each detail must fit with the given theme and instructions.
    - Write in a clear and easy-to-read way.
    - Do not explain or add comments about the story.
    - Do not use markdown or special formatting.
    - Return only one valid Python dictionary.
    - Follow exactly this structure:

    {
        "page_content": string (a short paragraph introducing the world in a vivid way),
        "metadata": {
            "world_name": "{{world_name}}" (in lowercase),
            "genre": "string" (e.g. 'fantasy', 'sci-fi', 'dark fantasy' etc., based on {{world_genre}}),
            "dominant_species": "string" (e.g. 'humans', 'elves', 'androids' etc.),
            "magic_presence": True or False (if magic exists in the world),
            "governance": "string" (e.g. 'monarchy', 'anarchy', 'federation' etc.)
        }
    }

    !!! DO NOT USE MARKDOWN OR FORMATTING LIKE ```python. OUTPUT ONLY A RAW PYTHON DICTIONARY. !!!
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get(
            "world_name",
            "World name not provided. Generate a default name.",
        ),
        world_genre=state.get("world_genre", "fantasy"),
        story_directives=state.get(
            "story_directives",
            "No specific directives provided. Generate a general narrative.",
        ),
    )
    truncated_prompt = truncate_structured_prompt(formatted_prompt)
    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    llm_dict: dict[str, str] = ast.literal_eval(llm_response)

    state["llm_generated_data"] = [llm_dict]
    state["create_new_character"] = True  # Set to True to prompt character creation
    state["world_context"] = llm_dict.get("page_content", "")
    return state


# ------------------------------------------------------------------ #
#                         CHARACTER FUNCTIONS                        #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Ask player if they want to create a new character")
def ask_create_new_character(state: StateSchema) -> StateSchema:
    cue = "Do you want to play as a new character? Respond by typing 'yes' or 'no'."
    response = get_player_answer(cue, force_type=True).lower()
    state["create_new_character"] = response in ["yes", "y"]
    return state


@traceable(run_type="chain", name="Ask for the name of the character")
def ask_new_character_name(state: StateSchema) -> StateSchema:
    if state.get("create_new_character"):
        cue = "How would you like to name your character? "
    else:
        cue = "What is the name of the character you want to play as? "

    character_name = get_player_answer(cue, force_type=True)
    state["character_name"] = character_name.strip().lower()
    state["user_input"] = character_name.strip()
    return state


@traceable(run_type="chain", name="Check if character exists")
def check_character_exists(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="characters",
    )
    result = db_collection.get(
        where={
            "$and": [
                {"world_id": state.get("world_id", "")},
                {"character_name": state.get("character_name", "")},
            ]
        }
    )
    character_exists = len(result["ids"]) > 0

    if character_exists and state.get("create_new_character"):
        cue = (
            f"The character '{state.get('character_name')}' already exists. "
            "Please restart the process and choose a different name."
        )
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_character"] = True
            return state
        else:
            raise ValueError(cue)
    elif not character_exists and not state.get("create_new_character"):
        cue = (
            f"The character '{state.get('character_name')}' does not exist. "
            "You must choose a different name or create a new character."
        )
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_character"] = True
            return state
        else:
            raise ValueError(cue)

    state["must_restart_character"] = False
    state["create_new_character"] = not character_exists
    state["character_id"] = result["ids"][0] if result["ids"] else str(uuid4())
    return state


@traceable(run_type="chain", name="Ask for character details")
def ask_character_details(state: StateSchema) -> StateSchema:
    character_gender = get_player_answer("What is your character's gender? ")
    character_description = get_player_answer("What is your character's description? ")

    state["character_gender"] = (
        character_gender.strip() if character_gender else "Generate a character gender"
    )
    state["character_description"] = (
        character_description.strip()
        if character_description
        else "Generate a character description"
    )

    return state


@traceable(run_type="chain", name="LLM Generate Character Data")
def llm_generate_character_data(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = "I am generating your character data. This may take a few moments, please be patient..."
        play_and_type(cue, width=TERMINAL_WIDTH)

    state["active_step"] = "character_creation"

    prompt_template = """
    ## ROLE
    You are a character creator for a procedural RPG game.  
    You make vivid, easy-to-imagine characters who fit well into fantasy or science-fiction worlds.

    ## OBJECTIVE
    Your task is to write a detailed and engaging character profile for "{{character_name}}" based on the following:

    - Character gender: {{character_gender}}
    - Character concept or description: "{{character_description}}"
    - World name: {{world_name}}
    - World ID: {{world_id}}

    Use the world as inspiration, but focus on making the character unique and memorable, with a clear personality, role, and background.  
    Use simple words and expressions so a 15-year-old teenager can understand everything.

    ## EXISTING CONTEXTS
    Here is information about the world to help guide your thinking:

    --- WORLD CONTEXT ---
    {{world_context}}
    ----------------------

    Here is lore that already exists for this world:

    --- EXISTING LORE CONTEXT ---
    {{lore_context}}
    -----------------------------

    ## FORMAT & STYLE
    - Write one strong paragraph describing the character’s past, personality traits, abilities, and role in the story.
    - Avoid overused ideas unless you twist them in an original way.
    - Keep it immersive but easy to read — like a game character codex.
    - Do NOT include markdown, YAML, or bullet points.
    - Output a single valid Python dictionary using exactly this format:

    {
        "page_content": "string" (a well-written character overview),
        "metadata": {
            "character_name": "{{character_name}}" (in lowercase),
            "world_id": "{{world_id}}",
            "world_name": "{{world_name}}" (in lowercase),
            "character_gender": "{{character_gender}}",
            "short_description": "short summary of the character's role and personality"
        }
    }

    !!! DO NOT USE MARKDOWN OR FORMATTING LIKE ```python. OUTPUT ONLY A RAW PYTHON DICTIONARY. !!!
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        character_name=state.get(
            "character_name",
            "Character name not provided. Generate a default name.",
        ),
        world_id=state.get("world_id", str(uuid4())),
        world_name=state.get(
            "world_name",
            "World name not provided. Generate a default name.",
        ),
        character_gender=state.get(
            "character_gender",
            "Character gender not provided. Generate a default gender.",
        ),
        character_description=state.get(
            "character_description",
            "Character description not provided. Generate a default description.",
        ),
        world_context=state.get("world_context", "No world context available yet."),
        lore_context=state.get("lore_context", "No lore context available yet."),
    )
    truncated_prompt = truncate_structured_prompt(formatted_prompt)
    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )
    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )
    llm_dict: dict[str, str] = ast.literal_eval(llm_response)
    state["llm_generated_data"] = [llm_dict]
    state["character_context"] = llm_dict.get("page_content", "")
    return state


# ------------------------------------------------------------------ #
#                      LORE GENERATION FUNCTIONS                     #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Get world context")
def get_world_context(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )
    result = db_collection.get(ids=[state.get("world_id", "")])

    if result["ids"]:
        state["world_context"] = result["documents"][0]
    else:
        state["world_context"] = "No context provided."

    return state


@traceable(run_type="chain", name="Get lore context")
def get_lore_context(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="lores",
    )

    retriever = db_collection.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 10,
            "lambda_mult": 0.2,  # 0 - 1
            "where": {"world_id": state.get("world_id", "")},
        },
    )

    query = f"Lore about the world {state.get('world_name', 'Unknown World')}"
    result = retriever.invoke(query)

    if len(result) > 0:
        state["lore_context"] = "\n".join([doc.page_content for doc in result])
    else:
        state["lore_context"] = "No lore context available yet."

    return state


@traceable(run_type="chain", name="Get character context")
def get_character_context(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="characters",
    )
    result = db_collection.get(where={"world_id": state.get("world_id", "")})

    if result["ids"]:
        state["character_context"] = "\n".join([doc for doc in result["documents"]])
    else:
        state["character_context"] = "No context provided."

    return state


@traceable(run_type="chain", name="LLM Generate Lore Data")
def llm_generate_lore_data(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = "I am now imagining an additional layer of depth to the lore. This may take a few moments, please be patient..."
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)

    state["active_step"] = "lore_generation"

    prompt_template = """
    ## ROLE
    You are a storyteller for a procedural RPG game.  
    You write exciting and mysterious background stories that make the game world "{{world_name}}" feel alive and full of secrets.

    ## OBJECTIVE
    Your job is to write one rich, standalone paragraph of lore about the world "{{world_name}}" (in normal case).  
    The text should feel like it comes from an old forgotten book, a story told around a campfire, or an important piece of the world's hidden history.  
    Use simple words and expressions so that a 15-year-old teenager can understand everything.

    ## EXISTING CONTEXTS
    Here is information about the world to help guide your story:

    --- WORLD CONTEXT ---
    {{world_context}}
    ----------------------

    Here is lore that already exists for this world:

    --- EXISTING LORE CONTEXT ---
    {{lore_context}}
    -----------------------------

    Here is character information that already exists for this world:

    --- EXISTING CHARACTER CONTEXT ---
    {{character_context}}
    -----------------------------

    ## FORMAT
    - Write only one detailed paragraph of lore in normal language.
    - Do not explain the story or add comments about it.
    - Do not use markdown, bullet points, or code formatting.
    - Give the answer as a raw Python dictionary exactly like this:

    {
        "page_content": "string" (a rich lore paragraph that adds to the world's story or history),
        "metadata": {
            "world_name": "{{world_name}}" (in lowercase),
            "world_id": "{{world_id}}",
            "type": "lore",
            "theme": "based on world context",
            "tags": "string listing the main themes or ideas" (e.g. 'ancient prophecy, lost kingdom, great battle')
        }
    }

    !!! DO NOT USE MARKDOWN OR FORMATTING LIKE ```python. OUTPUT ONLY A RAW PYTHON DICTIONARY. !!!
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get("world_name", "World name not provided."),
        world_context=state.get("world_context", "No world context available yet."),
        lore_context=state.get("lore_context", "No lore context available yet."),
        world_id=state.get("world_id", str(uuid4())),
    )
    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    llm_dict: dict[str, str] = ast.literal_eval(llm_response)

    state["llm_generated_data"] = [llm_dict]
    state["lore_context"] = llm_dict.get("page_content", "")
    return state


# ------------------------------------------------------------------ #
#                           STORY FUNCTIONS                          #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="LLM Generate World Summary")
def llm_generate_world_summary(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = "I am now summarizing your story. This may take a few moments, please be patient..."
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)

    prompt_template = """
    ## ROLE
    You are a world narrator for a procedural RPG game.  
    You tell the story of the world "{{world_name}}" in a simple, clear way.

    ## OBJECTIVE
    Write a short and immersive summary of "{{world_name}}".  
    It will be used:
    - At the start of the game to introduce the story,
    - At any time to remind players what has happened,
    - As an easy reference for players who may not speak English well.  

    Use simple words and expressions so a 15-year-old teenager can understand everything.

    ## INPUT CONTEXTS

    --- WORLD CONTEXT ---
    {{world_context}}

    --- LORE CONTEXT ---
    {{lore_context}}

    --- CHARACTER CONTEXT ---
    {{character_context}}

    ## STYLE & CONSTRAINTS
    - Use clear and easy-to-read language for non-native English speakers.
    - Summarize the main points of the world's story, history, events, and characters so far.
    - Avoid poetic or overly complicated language.
    - Keep names and sentences simple.
    - Tone should be neutral and informative, but still engaging.
    - You must talk directly to the player (use "you").
    - Do not include markdown, YAML, code blocks, or bullet points.

    ## FORMAT
    Return a **single raw string** of one or two short paragraphs (max ~100 words each) covering:
    - The current state and setting of the world
    - Key events that have happened so far
    - Any important characters or recent developments

    !!! DO NOT USE MARKDOWN, YAML, OR FORMATTING. OUTPUT ONLY A RAW STRING. !!!
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get("world_name", "World name not provided."),
        world_context=state.get("world_context", "No world context available yet."),
        lore_context=state.get("lore_context", "No lore context available yet."),
        character_context=state.get(
            "character_context", "No character context available yet."
        ),
        world_id=state.get("world_id", str(uuid4())),
    )

    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=0.3,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    if state.get("source") == "cli":
        print("\n")
        play_and_type(llm_response, width=TERMINAL_WIDTH)

    state["world_summary"] = llm_response
    return state


@traceable(run_type="chain", name="LLM Generate Immediate Event Summary")
def llm_generate_immediate_event_summary(state: StateSchema) -> StateSchema:
    prompt_template = """
    ## ROLE
    You are a world narrator for a procedural RPG game.  
    You tell the story of the world "{{world_name}}" in a simple, clear way.

    ## OBJECTIVE
    Write a short and immersive summary of what just happened.  
    It will be used to summarize players what choix they made.
    Use simple words and expressions so a 15-year-old teenager can understand everything.

    ## INPUT CONTEXTS

    --- EVENT CONTEXT ---
    {{event_context}}

    --- PLAYER ACTION WITHIN CONTEXT ---
    {{player_answer}}

    ## STYLE & CONSTRAINTS
    - Use clear and easy-to-read language for non-native English speakers.
    - Avoid poetic or overly complicated language.
    - Keep names and sentences simple.
    - Tone should be neutral and informative, but still engaging.
    - You must absolutely talk directly to the player (use "you").
    - Do not include markdown, YAML, code blocks, or bullet points.

    ## FORMAT
    Return a **single raw string** of one or two short paragraphs (max ~100 words each) covering:
    - The current state and setting of the story
    - The event that just happened

    !!! DO NOT USE MARKDOWN, YAML, OR FORMATTING. OUTPUT ONLY A RAW STRING. !!!
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get("world_name", "World name not provided."),
        event_context=state.get("event_context", "No event context available yet."),
        player_answer=state.get("player_answer", "No player answer available yet."),
    )

    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=0.3,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    if state.get("source") == "cli":
        print("\n")
        play_and_type(llm_response, width=TERMINAL_WIDTH)

    state["immediate_events"] = llm_response
    return state


@traceable(run_type="chain", name="Classify user message as yes or no")
def classify_user_message(state: StateSchema) -> StateSchema:
    user_message = state.get("user_message", "")
    
    if not user_message:
        state["classification_result"] = "no"
        return state

    # Create a simple classification prompt
    classification_prompt = f"""
    Classify the following user message as either 'yes' or 'no' based on whether the user wants to continue, proceed, or agrees with something.

    User message: "{user_message}"

    Rules:
    - If the user expresses desire to continue, proceed, agree, or any positive intent: respond with "yes"
    - If the user expresses desire to stop, disagree, or any negative intent: respond with "no"
    - If unclear, default to "no"
    
    Respond with only "yes" or "no", nothing else.
    """

    try:
        llm_model = ChatOpenAI(
            model=LLM_NAME,  # Cheaper model
            temperature=0.3,  # Low temperature for consistent classification
            streaming=False,
            max_retries=2,
        )

        raw_output = llm_model.invoke(classification_prompt).content
        llm_response = (
            raw_output.strip().lower() if isinstance(raw_output, str) else str(raw_output).strip().lower()
        )

        # Ensure we only get yes or no
        if "yes" in llm_response:
            state["classification_result"] = "yes"
        else:
            state["classification_result"] = "no"
            
    except Exception:
        # Default to "no" on error
        state["classification_result"] = "no"

    return state


# ------------------------------------------------------------------ #
#                         GAMEPLAY FUNCTIONS                         #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Retrieve past events for player")
def get_event_context(state: StateSchema) -> StateSchema:
    character_id = state.get("character_id")
    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )

    retriever = collection.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10},
    )
    results = retriever.invoke("What has happened so far in the story?")

    state["event_context"] = "\n".join([doc.page_content for doc in results])
    return state


@traceable(run_type="chain", name="LLM generate next narrative cue")
def llm_generate_next_prompt(state: StateSchema) -> StateSchema:
    prompt_template = """
    ## ROLE
    You are a story-driven game narrator.

    ## OBJECTIVE
    Based on the following context, generate a direct and immersive narrative prompt presenting a situation the player must respond to.
    The player must decide how to proceed in the unfolding story. He should consider his options carefully (for example, the player could make a choice between exploring a dark cave or returning to the safety of the village or the player could attempt to negotiate with a hostile NPC or prepare for a battle.)

    ## CONTEXT

    The player plays as the character named: {{character_name}}.

    --- WORLD CONTEXT ---
    {{world_context}}

    --- LORE CONTEXT ---
    {{lore_context}}

    --- CHARACTER CONTEXT ---
    {{character_context}}

    --- RECENT EVENTS ---
    {{event_context}}

    ## OUTPUT FORMAT
    - Output one engaging paragraph in plain text. 
    - You must talk directly to the player (use "you").
    - End with an actionnable, concrete question or dilemma regarding an immediate situation.

    !!! DO NOT INCLUDE MARKDOWN OR CODE FORMATTING !!!
    """
    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_context=state.get("world_context", ""),
        event_context=state.get("event_context", ""),
        lore_context=state.get("lore_context", ""),
        character_context=state.get("character_context", ""),
        character_name=state.get("character_name", "")
    )

    llm_model = ChatOpenAI(model=LLM_NAME, temperature=MAIN_TEMP)
    result = llm_model.invoke(truncate_structured_prompt(formatted_prompt)).content
    result = result.strip() if isinstance(result, str) else str(result)

    # Save in collection
    character_id = state.get("character_id")
    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )

    doc = Document(
        page_content=result,
        metadata={
            "source": "AI",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    collection.add_documents([doc])
    state["ai_question"] = result

    if state.get("source") == "cli":
        print("\n")
        play_and_type(result, width=TERMINAL_WIDTH)

    return state


@traceable(run_type="chain", name="Record player response")
def record_player_response(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        time.sleep(7.5)
        state["player_answer"] = get_player_answer("What do you want to do? ")
    character_id = state.get("character_id")
    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )
    doc = Document(
        page_content=state.get("player_answer", ""),
        metadata={
            "source": "player",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    collection.add_documents([doc])
    return state


@traceable(run_type="chain", name="Ask if player wants to continue")
def ask_to_continue_or_stop(state: StateSchema) -> StateSchema:
    time.sleep(7.5)
    cue = "Do you wish to continue? Respond by typing 'yes' or 'no'."
    answer = get_player_answer(cue, force_type=True).strip().lower()
    state["continue_story"] = answer in ["yes", "y"]
    return state


# ------------------------------------------------------------------ #
#                          UTILITY FUNCTIONS                         #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Save list of documents to ChromaDB")
def save_documents_to_chroma(state: StateSchema) -> StateSchema:
    world_id = state.get("world_id", "")
    llm_generated_data = state.get("llm_generated_data", [])

    # Convert to LangChain Document format
    documents_to_save = [
        Document(
            page_content=document.get("page_content", ""),
            metadata=document.get("metadata", {}),
        )
        for document in llm_generated_data
    ]

    if state.get("active_step") == "world_creation":
        ids = [world_id]
        collection_name = "worlds"
    elif state.get("active_step") == "lore_generation":
        ids = [str(uuid4()) for _ in documents_to_save]
        collection_name = "lores"
    elif state.get("active_step") == "character_creation":
        ids = [str(uuid4()) for _ in documents_to_save]
        collection_name = "characters"
    else:
        ids = [str(uuid4()) for _ in documents_to_save]
        collection_name = "test"

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=collection_name,
    )

    db_collection.add_documents(documents_to_save, ids=ids)
    return state


# ------------------------------------------------------------------ #
#                   CONDITIONAL VALIDATOR FUNCTIONS                  #
# ------------------------------------------------------------------ #


def check_input_validity(
    state: StateSchema,
) -> Literal["__valid__", "__invalid__"]:
    res = "__valid__"

    if not state.get("user_input"):
        cue = "It seems you haven't provided any input. Let's try again."
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)
        res = "__invalid__"

    state["user_input"] = ""
    return res


# ------------------------------------------------------------------ #
#                               ROUTERS                              #
# ------------------------------------------------------------------ #


def route_world_creation(
    state: StateSchema,
) -> Literal["__exists__", "__must_configure__", "__must_restart_init__"]:
    if state.get("must_restart_init"):
        return "__must_restart_init__"
    elif state.get("create_new_world"):
        return "__must_configure__"
    else:
        return "__exists__"


def route_character_creation(
    state: StateSchema,
) -> Literal["__exists__", "__must_configure__", "__must_restart_character__"]:
    if state.get("must_restart_character"):
        return "__must_restart_character__"
    elif state.get("create_new_character"):
        return "__must_configure__"
    else:
        return "__exists__"


def route_after_saving(
    state: StateSchema,
) -> Literal["__from_world__", "__from_lore__", "__from_character__"]:
    if state.get("active_step") == "world_creation":
        return "__from_world__"
    elif state.get("active_step") == "character_creation":
        return "__from_character__"
    else:
        return "__from_lore__"


# ------------------------------------------------------------------ #
#                                GRAPH                               #
# ------------------------------------------------------------------ #

graph = StateGraph(StateSchema)

# ------------------------------ Nodes ----------------------------- #

# World Generation Nodes
graph.add_node("ask_if_new_world", ask_if_new_world)
graph.add_node("ask_world_name", ask_world_name)
graph.add_node("check_world_exists", check_world_exists)
graph.add_node("ask_world_genre", ask_world_genre)
graph.add_node("ask_story_directives", ask_story_directives)
graph.add_node("llm_generate_world_data", llm_generate_world_data)

# Character Creation Nodes
graph.add_node("ask_create_new_character", ask_create_new_character)
graph.add_node("ask_new_character_name", ask_new_character_name)
graph.add_node("check_character_exists", check_character_exists)
graph.add_node("ask_character_details", ask_character_details)
graph.add_node("llm_generate_character_data", llm_generate_character_data)

# Lore Generation Nodes
graph.add_node("get_world_context", get_world_context)
graph.add_node("get_lore_context", get_lore_context)
graph.add_node("get_character_context", get_character_context)
graph.add_node("llm_generate_lore_data", llm_generate_lore_data)

# World Summary Nodes
graph.add_node("llm_generate_world_summary", llm_generate_world_summary)

# Gameplay Nodes
graph.add_node("get_event_context", get_event_context)
graph.add_node("llm_generate_next_prompt", llm_generate_next_prompt)
graph.add_node("record_player_response", record_player_response)
graph.add_node("ask_to_continue_or_stop", ask_to_continue_or_stop)

# Validators
graph.add_node("check_input_validity", check_input_validity)

# Routing Nodes
graph.add_node("route_character_creation", route_character_creation)
graph.add_node("route_world_creation", route_world_creation)
graph.add_node("route_after_saving", route_after_saving)

# Utility Functions
graph.add_node("save_documents_to_chroma", save_documents_to_chroma)

# ---------------------------- Workflow ---------------------------- #

# Entry point
graph.set_entry_point("ask_if_new_world")

# Ask if player wants to create a new world block
graph.add_edge("ask_if_new_world", "ask_world_name")
graph.add_conditional_edges(
    "ask_world_name",
    check_input_validity,
    {
        "__valid__": "check_world_exists",
        "__invalid__": "ask_world_name",
    },
)
graph.add_conditional_edges(
    "check_world_exists",
    route_world_creation,
    {
        "__must_restart_init__": "ask_if_new_world",
        "__must_configure__": "ask_world_genre",
        "__exists__": "ask_create_new_character",
    },
)

# World creation block
graph.add_edge("ask_world_genre", "ask_story_directives")
graph.add_edge("ask_story_directives", "llm_generate_world_data")
graph.add_edge("llm_generate_world_data", "save_documents_to_chroma")

# Character creation block
graph.add_edge("ask_create_new_character", "ask_new_character_name")
graph.add_conditional_edges(
    "ask_new_character_name",
    check_input_validity,
    {
        "__valid__": "check_character_exists",
        "__invalid__": "ask_new_character_name",
    },
)
graph.add_conditional_edges(
    "check_character_exists",
    route_character_creation,
    {
        "__must_restart_character__": "ask_create_new_character",
        "__must_configure__": "ask_character_details",
        "__exists__": "get_world_context",
    },
)
graph.add_edge("ask_character_details", "llm_generate_character_data")
graph.add_edge("llm_generate_character_data", "save_documents_to_chroma")

# Lore creation block
graph.add_edge("get_world_context", "get_lore_context")
graph.add_edge("get_lore_context", "get_character_context")
graph.add_edge("get_character_context", "llm_generate_lore_data")
graph.add_edge("llm_generate_lore_data", "save_documents_to_chroma")

# Routing after saving documents block
graph.add_conditional_edges(
    "save_documents_to_chroma",
    route_after_saving,
    {
        "__from_world__": "ask_new_character_name",
        "__from_character__": "get_world_context",
        "__from_lore__": "llm_generate_world_summary",
    },
)

graph.add_edge("llm_generate_world_summary", "ask_to_continue_or_stop")

# World summary generation block
graph.add_edge("get_event_context", "llm_generate_next_prompt")
graph.add_edge("llm_generate_next_prompt", "record_player_response")
graph.add_edge("record_player_response", "ask_to_continue_or_stop")

graph.add_conditional_edges(
    "ask_to_continue_or_stop",
    lambda state: "__continue__" if state.get("continue_story") else "__end__",
    {
        "__continue__": "get_event_context",
        "__end__": END,
    },
)

# Final state
main_graph = graph.compile()
