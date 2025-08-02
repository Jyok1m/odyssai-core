# Libs
import os
import chromadb
import ast
from uuid import uuid4
from functools import partial
from typing_extensions import TypedDict, Literal, Required, NotRequired

# Langchain
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langsmith import traceable

# Modules
from ..utils.prompt_truncation import truncate_structured_prompt
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from ..constants.llm_models import LLM_NAME, EMBEDDING_MODEL
from ..constants.interaction_cues import WORLD_BUILDING_CUES

# Static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)

# ENVIRONMENT VARIABLES

# ------------------------------------------------------------------ #
#                                SCHEMA                              #
# ------------------------------------------------------------------ #


class StateSchema(TypedDict):
    world_id: NotRequired[str]
    world_name: NotRequired[str]
    world_genre: NotRequired[str]
    story_directives: NotRequired[str]
    create_new_world: NotRequired[bool]
    user_input: NotRequired[str]


# ------------------------------------------------------------------ #
#                      INITIALISATION FUNCTIONS                      #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Ask player if they want to create a new world")
def ask_if_new_world(state: StateSchema) -> StateSchema:
    response = input("Do you want to create a new world? (yes/no): ").strip().lower()
    state["create_new_world"] = response in ["yes", "y"]
    return state


@traceable(run_type="chain", name="Ask for the name of the world")
def ask_world_name(state: StateSchema) -> StateSchema:
    if state.get("create_new_world"):
        world_name = input(
            "What is the name of the new world you would like to create? "
        )
    else:
        world_name = input("What is the name of the world you would like to join? ")

    state["world_name"] = world_name.strip()
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
    print(f"World exists: {world_exists} {state.get('world_name')}")
    state["create_new_world"] = not world_exists
    return state


@traceable(run_type="chain", name="Ask for the genre of the world")
def ask_world_genre(state: StateSchema) -> StateSchema:
    world_genre = input(
        "What would be the genre of the world you would like to adventure in? (e.g., medieval, cyberpunk, fantasy, realistic...) "
    )
    state["world_genre"] = world_genre.strip()
    state["user_input"] = world_genre.strip()
    return state


@traceable(run_type="chain", name="Ask for story directives")
def ask_story_directives(state: StateSchema) -> StateSchema:
    story_directives = input(
        "Do you have any specific narrative directives or themes you'd like the story to follow? (e.g., rebellion, survival, I want a story based on bond creation, friendship and alliances...) "
    )
    state["story_directives"] = story_directives.strip()
    state["user_input"] = story_directives.strip()
    return state


# ------------------------------------------------------------------ #
#                   CONDITIONAL VALIDATOR FUNCTIONS                  #
# ------------------------------------------------------------------ #


def check_input_validity(
    state: StateSchema,
) -> Literal["__valid__", "__invalid__"]:
    res = "__valid__"

    if not state.get("user_input"):
        res = "__invalid__"

    state["user_input"] = ""
    return res


def route_world_creation(
    state: StateSchema,
) -> Literal["__exists__", "__must_configure__"]:
    return "__must_configure__" if state.get("create_new_world") else "__exists__"


# ------------------------------------------------------------------ #
#                                GRAPH                               #
# ------------------------------------------------------------------ #

graph = StateGraph(StateSchema)

# ------------------------------ Nodes ----------------------------- #

graph.add_node("ask_if_new_world", ask_if_new_world)
graph.add_node("ask_world_name", ask_world_name)
graph.add_node("check_input_validity", check_input_validity)
graph.add_node("check_world_exists", check_world_exists)
graph.add_node("route_world_creation", route_world_creation)
graph.add_node("ask_world_genre", ask_world_genre)
graph.add_node("ask_story_directives", ask_story_directives)

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
    {"__must_configure__": "ask_world_genre", "__exists__": END},
)
graph.add_conditional_edges(
    "ask_world_genre",
    check_input_validity,
    {"__valid__": "ask_story_directives", "__invalid__": "ask_world_genre"},
)
graph.add_conditional_edges(
    "ask_story_directives",
    check_input_validity,
    {"__valid__": END, "__invalid__": "ask_story_directives"},
)

main_graph = graph.compile()
