# Libs
from .world_graph import world_creation_graph
import chromadb
import ast
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict, Required, NotRequired
from uuid import uuid4

# Modules
from ..utils.prompt_truncation import truncate_structured_prompt
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from ..constants.llm_models import LLM_NAME, EMBEDDING_MODEL

# Initialize static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)

# ------------------------------------------------------------------ #
#                            SHARED STATE                            #
# ------------------------------------------------------------------ #


# WorldState
class WorldState(TypedDict):
    world_name: Required[str]

    # Optional as inputs:
    world_id: NotRequired[str]
    world_setting: NotRequired[str]
    story_directives: NotRequired[str]
    llm_dict: NotRequired[dict[str, str]]
    lc_document: NotRequired[Document]
    world_already_exists: NotRequired[bool]


# ------------------------------------------------------------------ #
#                              FUNCTIONS                             #
# ------------------------------------------------------------------ #


def check_world_exists(state: WorldState) -> str:
    if state.get("world_already_exists", False):
        print("World already exists, skipping creation.")
        return "__end__"
    print("World does not exist, proceeding with creation.")
    return "__continue__"


def get_world_id(state: WorldState) -> WorldState:
    """Retrieve or create a unique world ID based on the world name."""
    print("Retrieving or creating world ID...")

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )

    result = db_collection.get(where={"world_name": state["world_name"]})

    if len(result["ids"]) > 0:
        world_id = result["ids"][0]
        state["world_already_exists"] = True
    else:
        world_id = str(uuid4())

    print("World ID retrieved or created. Moving on...")
    return {**state, "world_id": world_id}


def create_world(state: WorldState) -> WorldState:
    """Generate a world dictionary using the LLM based on user inputs."""

    print("Creating world dictionary data...")

    prompt_template = """
    ## ROLE
    You are a narrative generator for a procedural RPG game.

    ## OBJECTIVE
    Your task is to generate an overview of the world "{{world_name}}".

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
            "world_name": "{{world_name}}",
            "genre": "string" (e.g. 'fantasy', 'sci-fi', 'dark fantasy' etc... based on the genre: {{world_genre}}),
            "dominant_species": "string" (e.g. 'humans', 'elves', 'androids' etc...),
            "magic_presence": True or False (whether magic exists in the world),
            "governance": "string" (e.g. 'monarchy', 'anarchy', 'federation' etc...)
        }
    }
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state["world_name"],
        world_genre=state.get("world_setting", "fantasy"),
        story_directives=state.get(
            "story_directives", "No specific directives provided."
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
    if isinstance(raw_output, str):
        llm_response = raw_output.strip()
    else:
        llm_response = str(raw_output)

    llm_dict: dict[str, str] = ast.literal_eval(llm_response)

    print("World dictionary data created successfully. Moving on...")
    return {**state, "llm_dict": llm_dict}


def convert_to_langchain_document(state: WorldState) -> WorldState:
    """
    Convert the LLM response into a Document format suitable for storage.
    """
    print("Converting LLM response to LangChain Document...")

    llm_dict = state.get("llm_dict", {})
    lc_document = Document(
        page_content=llm_dict.get("page_content", ""),
        metadata=llm_dict.get("metadata", {}),
    )

    print("Conversion to LangChain Document completed successfully. Moving on...")
    return {**state, "lc_document": lc_document}


def save_document_to_chroma(state: WorldState) -> WorldState:
    """
    Save the generated document to the Chroma database.
    """
    print("Saving LangChain Document to Chroma database...")

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )

    lc_document = state.get("lc_document")
    document_id = state.get("world_id", str(uuid4()))

    if lc_document:
        db_collection.add_documents([lc_document], ids=[document_id])

    print("Document saved to Chroma database successfully.")
    return {**state}


# ------------------------------------------------------------------ #
#                            Graph builder                           #
# ------------------------------------------------------------------ #


graph = StateGraph(WorldState)

graph.add_node("get_world_id", get_world_id)
graph.add_node("create_world", create_world)
graph.add_node("convert_to_langchain_document", convert_to_langchain_document)
graph.add_node("save_document_to_chroma", save_document_to_chroma)

graph.add_node("world_creation_graph", world_creation_graph)

graph.set_entry_point("get_world_id")
graph.add_conditional_edges(
    "get_world_id", check_world_exists, {"__continue__": "create_world", "__end__": END}
)
graph.add_edge("create_world", "convert_to_langchain_document")
graph.add_edge("convert_to_langchain_document", "save_document_to_chroma")
graph.add_edge("save_document_to_chroma", END)

graph.add_edge("ask_world_name", "world_creation_graph")
graph.add_edge("world_creation_graph", END)

world_creation_graph = graph.compile()
