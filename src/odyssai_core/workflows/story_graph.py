# Libs
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
from ..workflows.ask_user_graph import QuestionState, ask_user_graph
from ..workflows.lore_graph import LoreState, get_world_context, get_lore_context
from ..utils.prompt_truncation import truncate_structured_prompt
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from ..constants.llm_models import LLM_NAME, EMBEDDING_MODEL

# Initialize static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)

# ------------------------------------------------------------------ #
#                            SHARED STATE                            #
# ------------------------------------------------------------------ #


# WorldState
class StoryState(TypedDict):
    world_id: Required[str]

    # Optional as inputs:
    world_name: NotRequired[str]
    initial_context: NotRequired[str]
    initial_resume: NotRequired[dict[str, str]]
    character_data: NotRequired[dict[str, str]]


# ------------------------------------------------------------------ #
#                              FUNCTIONS                             #
# ------------------------------------------------------------------ #


# Step 1: Get Story Context
def get_initial_context(state: StoryState) -> StoryState:
    """Get the initial context for the story workflow."""

    # Get the world and lore contexts
    lore_state = LoreState(world_id=state["world_id"])
    world_context_state = get_world_context(lore_state)
    lore_context_state = get_lore_context(lore_state)

    combined_context = f"""
    - World context:\n{world_context_state}\n\n
    - Lore context:\n{lore_context_state}
    """

    return {**state, "initial_context": combined_context}


# Step 2: Get world name from DB
def get_world_name(state: StoryState) -> StoryState:
    """Get the world name from the user or use a default value."""

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )

    result = db_collection.get(ids=state["world_id"])
    world_name = result["metadata"][0].get("world_name", "Unnamed World")

    return {**state, "world_name": world_name}


# Step 3: Create Initial Résumé from Context
def create_initial_resume(state: StoryState) -> StoryState:
    """Generate a résumé based on the initial context using the LLM."""

    prompt_template = """
    ## ROLE
    You are a narrative generator for a procedural RPG game.

    ## OBJECTIVE
    Your task is to generate a compelling story based on the provided world and lore contexts.

    ## CREATIVE EXPECTATIONS
    - Get inspiration from the current world and lore contexts.
    - Ensure narrative consistency with established contexts.
    - Avoid redundancy, ensuring each part contributes to meaningful story development.
    - Create a starting point for the player: emphasize causal relationships, evolution of the world, and potential narrative tension points the player may be involved with during his playthrough.

    ## CONTEXTS

    {{initial_context}}

    ## FORMAT
    - Write in an easy-to-read manner.
    - Return a single string with the content.
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        initial_context=state.get("initial_context", "No context provided.")
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

    initial_resume = ast.literal_eval(llm_response)

    return {**state, "initial_resume": initial_resume}


# Step 4: Print the initial resume
def print_initial_resume(state: StoryState) -> StoryState:
    """Print the initial resume to the console."""
    print("Initial Resume:")
    print(state.get("initial_resume", "No initial resume available."))
    return state


# Step 5: Ask user questions to create his character
def generate_character_data(state: StoryState) -> StoryState:
    """Ask the user questions to create their character using the ask_user_graph."""
    result = ask_user_graph.invoke({"query_type": "character"})
    user_answers = result.get("responses", {})

    # Store the responses in the state
    return {**state, "character_data": user_answers}


# Step 6: Ask chatGPT to create the character document


def convert_to_langchain_documents(state: LoreState) -> LoreState:
    """
    Convert the LLM response into a list of Document formats suitable for storage.
    """
    print("Converting LLM response to LangChain Documents...")

    llm_list = state.get("llm_list", [])
    lc_documents = [
        Document(
            page_content=item.get("page_content", ""),
            metadata=item.get("metadata", {}),
        )
        for item in llm_list
    ]

    print("Conversion to LangChain Documents completed successfully. Moving on...")
    return {**state, "lc_documents": lc_documents}


def save_documents_to_chroma(state: LoreState) -> LoreState:
    """
    Save the generated documents to the Chroma database.
    """
    print("Saving LangChain Documents to Chroma database...")

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="lores",
    )

    lc_documents = state.get("lc_documents", [])
    if lc_documents:
        document_ids = [str(uuid4()) for _ in lc_documents]
        db_collection.add_documents(lc_documents, ids=document_ids)

    print("Documents saved to Chroma database successfully.")
    return {**state}


# ------------------------------------------------------------------ #
#                            Graph builder                           #
# ------------------------------------------------------------------ #


graph = StateGraph(StoryState)

graph.add_node("get_initial_context", get_initial_context)
graph.add_node("create_initial_resume", create_initial_resume)
graph.add_node("get_world_name", get_world_name)
graph.add_node("print_initial_resume", print_initial_resume)
graph.add_node("generate_character_data", generate_character_data)

# graph.add_node("get_world_context", get_world_context)
# graph.add_node("get_lore_context", get_lore_context)
# graph.add_node("create_lore", create_lore)
# graph.add_node("convert_to_langchain_documents", convert_to_langchain_documents)
# graph.add_node("save_documents_to_chroma", save_documents_to_chroma)

# graph.set_entry_point("get_world_context")
# graph.add_edge("get_world_context", "create_lore")
# graph.add_edge("create_lore", "convert_to_langchain_documents")
# graph.add_edge("convert_to_langchain_documents", "save_documents_to_chroma")
# graph.add_edge("save_documents_to_chroma", END)

# lore_graph = graph.compile()
