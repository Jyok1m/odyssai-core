# Libs
import os
import chromadb
import ast
import textwrap
import shutil
from uuid import uuid4
from functools import partial
from typing_extensions import TypedDict, Literal, Required, NotRequired

# Langchain
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langsmith import traceable

# Modules
from ..utils.prompt_truncation import truncate_structured_prompt
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from ..constants.llm_models import LLM_NAME, EMBEDDING_MODEL

# Static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)
TERMINAL_WIDTH = shutil.get_terminal_size((80, 20)).columns

# ------------------------------------------------------------------ #
#                                SCHEMA                              #
# ------------------------------------------------------------------ #


class StateSchema(TypedDict):
    # World Data
    world_id: NotRequired[str]
    world_name: NotRequired[str]
    llm_gen_data: NotRequired[list[dict[str, str]]]  # Swap data for better handling

    # Init Data
    world_genre: NotRequired[str]
    story_directives: NotRequired[str]
    create_new_world: NotRequired[bool]
    must_restart_init: NotRequired[bool]
    user_input: NotRequired[str]


# ------------------------------------------------------------------ #
#                      INITIALISATION FUNCTIONS                      #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Ask player if they want to create a new world")
def ask_if_new_world(state: StateSchema) -> StateSchema:
    cue = "Do you want to create a new world? (y/n)"
    print(textwrap.fill(f"\nAI: {cue}", width=TERMINAL_WIDTH))
    response = input(" Answer: ").strip().lower()
    state["create_new_world"] = response in ["yes", "y"]
    return state


@traceable(run_type="chain", name="Ask for the name of the world")
def ask_world_name(state: StateSchema) -> StateSchema:
    if state.get("create_new_world"):
        cue = (
            "What would you like to name your world? "
            "You can choose a name that reflects its history, culture, dominant species, "
            "or simply something that sounds powerful, mystical, or poetic."
        )
    else:
        cue = (
            "Which existing world would you like to enter? "
            "You may choose a known realm you’ve visited before, "
            "or mention one by name if you’ve heard whispers of its legend."
        )
    print(textwrap.fill(f"\nAI: {cue}", width=TERMINAL_WIDTH))
    world_name = input(" Answer: ")
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
        print(textwrap.fill(f"\nAI: ❌ {cue}", width=TERMINAL_WIDTH))
        state["must_restart_init"] = True
        return state
    elif not world_exists and not state.get("create_new_world"):
        cue = (
            f"The world '{state.get('world_name')}' does not exist. "
            "You must choose a different name or create a new world."
        )
        print(textwrap.fill(f"\nAI: ❌ {cue}", width=TERMINAL_WIDTH))
        state["must_restart_init"] = True
        return state

    state["must_restart_init"] = False
    state["create_new_world"] = not world_exists
    state["world_id"] = result["ids"][0] if result["ids"] else str(uuid4())
    return state


@traceable(run_type="chain", name="Ask for the genre of the world")
def ask_world_genre(state: StateSchema) -> StateSchema:
    cue = (
        "Describe the world’s main genre — "
        "is it hopeful or grim, ancient or futuristic, magical or technological? "
        "Give as much detail as you’d like."
    )

    print(textwrap.fill(f"\nAI: {cue}", width=TERMINAL_WIDTH))
    world_genre = input(" Answer: ")
    state["world_genre"] = world_genre.strip()
    state["user_input"] = world_genre.strip()
    return state


@traceable(run_type="chain", name="Ask for story directives")
def ask_story_directives(state: StateSchema) -> StateSchema:
    cue = (
        "Are there particular themes or narrative threads you’d like to explore? "
        "Think in terms of emotional arcs (e.g. redemption, betrayal), "
        "overarching goals (e.g. building alliances, resisting tyranny), "
        "or narrative tones (e.g. tragic, hopeful, mysterious). "
        "Let your imagination guide the story’s soul."
    )

    print(textwrap.fill(f"\nAI: {cue}", width=TERMINAL_WIDTH))
    story_directives = input(" Answer: ")
    state["story_directives"] = story_directives.strip()
    state["user_input"] = story_directives.strip()
    return state


# ------------------------------------------------------------------ #
#                     WORLD GENERATION FUNCTIONS                     #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="LLM Generate World Data")
def llm_generate_world_data(state: StateSchema) -> StateSchema:
    prompt_template = """
    ## ROLE
    You are a narrative generator for a procedural RPG game.

    ## OBJECTIVE
    Your task is to generate an overview of the world "{{world_name}}" (in Normal case).

    ## CREATIVE EXPECTATIONS
    - The theme of the world must be: {{world_genre}}
    - You must respect the following directives: {{story_directives}}

    ## FORMAT
    - Each value must be coherent with the creative expectations.
    - Write in an easy-to-read manner.
    - Do not include any explanations, comments, or markdown formatting.
    - Return a single valid Python dictionary.
    - Respect the following dictionary structure:
    {
        "page_content": string (short descriptive paragraph introducing the world),
        "metadata": {
            "world_name": "{{world_name}}" (in lowercase),
            "genre": "string" (e.g. 'fantasy', 'sci-fi', 'dark fantasy' etc... based on the genre: {{world_genre}}),
            "dominant_species": "string" (e.g. 'humans', 'elves', 'androids' etc...),
            "magic_presence": True or False (whether magic exists in the world),
            "governance": "string" (e.g. 'monarchy', 'anarchy', 'federation' etc...)
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
        temperature=0.7,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    llm_dict: dict[str, str] = ast.literal_eval(llm_response)

    state["llm_gen_data"] = [llm_dict]
    return state


# @traceable(run_type="chain", name="Get world ID")
# def get_or_create_world_id(state: StateSchema) -> StateSchema:
#     db_collection = Chroma(
#         client=CHROMA_DB_CLIENT,
#         embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
#         collection_name="worlds",
#     )
#     result = db_collection.get(where={"world_name": state.get("world_name", "")})
#     state["world_id"] = result["ids"][0] if result["ids"] else str(uuid4())
#     return state


# ------------------------------------------------------------------ #
#                   CONDITIONAL VALIDATOR FUNCTIONS                  #
# ------------------------------------------------------------------ #


def check_input_validity(
    state: StateSchema,
) -> Literal["__valid__", "__invalid__"]:
    res = "__valid__"

    if not state.get("user_input"):
        cue = "It seems you haven't provided any input. Let's try again."
        print(textwrap.fill(f"\nAI: {cue}", width=TERMINAL_WIDTH))
        res = "__invalid__"

    state["user_input"] = ""
    return res


def route_world_creation(
    state: StateSchema,
) -> Literal["__exists__", "__must_configure__", "__must_restart_init__"]:
    if state.get("must_restart_init"):
        return "__must_restart_init__"
    elif state.get("create_new_world"):
        return "__must_configure__"
    else:
        return "__exists__"


# ------------------------------------------------------------------ #
#                                GRAPH                               #
# ------------------------------------------------------------------ #

graph = StateGraph(StateSchema)

# ------------------------------ Nodes ----------------------------- #

# Initialisation Nodes
graph.add_node("ask_if_new_world", ask_if_new_world)
graph.add_node("ask_world_name", ask_world_name)
graph.add_node("check_world_exists", check_world_exists)
graph.add_node("ask_world_genre", ask_world_genre)
graph.add_node("ask_story_directives", ask_story_directives)

# World Generation Nodes
graph.add_node("llm_generate_world_data", llm_generate_world_data)
# graph.add_node("get_or_create_world_id", get_or_create_world_id)

# Validators
graph.add_node("check_input_validity", check_input_validity)
graph.add_node("route_world_creation", route_world_creation)

# ---------------------------- Workflow ---------------------------- #

# Entry point
graph.set_entry_point("ask_if_new_world")

# Transitions
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
        "__exists__": END,
    },
)
graph.add_conditional_edges(
    "ask_world_genre",
    check_input_validity,
    {"__valid__": "ask_story_directives", "__invalid__": "ask_world_genre"},
)
graph.add_conditional_edges(
    "ask_story_directives",
    check_input_validity,
    {"__valid__": "llm_generate_world_data", "__invalid__": "ask_story_directives"},
)
graph.add_edge("llm_generate_world_data", END)

main_graph = graph.compile()
