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
from ..utils.prompt_truncation import truncate_structured_prompt
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from ..constants.llm_models import LLM_NAME, EMBEDDING_MODEL

# Initialize static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)

# ------------------------------------------------------------------ #
#                            SHARED STATE                            #
# ------------------------------------------------------------------ #


# WorldState
class LoreState(TypedDict):
    world_id: Required[str]

    # Optional as inputs:
    world_context: NotRequired[str]
    lore_context: NotRequired[str]
    player_id: NotRequired[str]
    llm_list: NotRequired[list[dict[str, str]]]
    lc_documents: NotRequired[list[Document]]


# ------------------------------------------------------------------ #
#                              FUNCTIONS                             #
# ------------------------------------------------------------------ #


def get_world_context(state: LoreState) -> LoreState:
    """Retrieve the world context based on world_id."""
    print("Retrieving the world context...")

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )

    result = db_collection.get(ids=state["world_id"])

    if state.get("world_context"):
        print("World context already provided, skipping retrieval.")
        return {
            **state,
            "world_context": state.get("world_context", "No context provided."),
        }
    elif len(result["ids"]) > 0:
        world_context = result["documents"][0]
    else:
        world_context = "No context provided."

    print("World context retrieved successfully.")
    return {**state, "world_context": world_context}


def get_lore_context(state: LoreState) -> LoreState:
    """Retrieve the lore context based on world_id."""
    print("Retrieving the lore context...")

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="lores",
    )

    retriever = db_collection.as_retriever(
        search_type="mmr",
        search_kwargs={"where": {"world_id": state["world_id"]}},
    )

    result = retriever.get_relevant_documents(
        query="What are the best documents about lore in this world?",
        context=state.get("lore_context", "No context provided."),
    )

    if len(result) > 0:
        lore_context = "\n".join([doc.page_content for doc in result])
    else:
        lore_context = "No lore context available."

    print("Lore context retrieved successfully.")
    return {**state, "lore_context": lore_context}


def create_lore(state: LoreState) -> LoreState:
    """Generate a lore dictionary using the LLM based on user inputs."""

    print("Creating lore context data...")

    prompt_template = """
    ## ROLE
    You are a narrative generator for a procedural RPG game.

    ## OBJECTIVE
    Your task is to generate 5 lore entries for the world: "{{world_name}}".

    ## CREATIVE EXPECTATIONS
    - Get inspiration from the current world context.
    - You must remain consistent.
    - Each event must be narratively consistent with the established contexts. 
    - Avoid redundancy, and ensure each entry contributes to meaningful story development.
    - Below are excerpts of previously generated content. Use them to remain coherent.

    ## CONTEXTS

    - World context: 

    {{world_context}}

    - Lore context:

    {{lore_context}}

    ## FORMAT
    - Each value must be coherent with the creative expectations.
    - Write in an easy-to-read manner.
    - Do not include any explanations, comments, or markdown formatting.
    - Return a list of single valid Python dictionaries.
    - Respect the following dictionary structure:
    {
        "page_content": "string" (short narrative paragraph in English for the lore entry),
        "metadata": {
            "world_id": "{{world_id}}",
            "related_world": "{{world_name}}",
            "theme": "string" (main narrative or conceptual theme, e.g. 'cosmology', 'faith', 'magic'),
            "importance": "major | minor | local"
        }
    }
    """

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state["world_id"],
        world_id=state["world_id"],
        world_context=state.get("world_context", "No context provided."),
        lore_context=state.get("lore_context"),
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

    llm_list: list[dict[str, str]] = ast.literal_eval(llm_response)

    print("World dictionary data created successfully. Moving on...")
    return {**state, "llm_list": llm_list}


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


graph = StateGraph(LoreState)

graph.add_node("get_world_context", get_world_context)
graph.add_node("get_lore_context", get_lore_context)
graph.add_node("create_lore", create_lore)
graph.add_node("convert_to_langchain_documents", convert_to_langchain_documents)
graph.add_node("save_documents_to_chroma", save_documents_to_chroma)

graph.set_entry_point("get_world_context")
graph.add_edge("get_world_context", "create_lore")
graph.add_edge("create_lore", "convert_to_langchain_documents")
graph.add_edge("convert_to_langchain_documents", "save_documents_to_chroma")
graph.add_edge("save_documents_to_chroma", END)

lore_graph = graph.compile()
