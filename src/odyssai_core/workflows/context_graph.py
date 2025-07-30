import chromadb

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END

from typing_extensions import TypedDict, Literal, Required, NotRequired, cast
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE

# Initialize static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)
EMBEDDING_MODEL = "text-embedding-3-small"


# State
class State(TypedDict):
    world_id: Required[str]
    context_type: Required[Literal["world", "lore", "event", "character"]]
    world_context: NotRequired[str]
    lore_context: NotRequired[str]
    event_context: NotRequired[str]
    character_context: NotRequired[str]
    retrieved_documents: NotRequired[list[Document]]


# ------------------------------------------------------------------ #
#                              Functions                             #
# ------------------------------------------------------------------ #


def get_context_docs_from_collection(state: State) -> State:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{state['context_type']}s",
    )

    retriever = db_collection.as_retriever(
        search_kwargs={"k": 10, "filter": {"world_id": state["world_id"]}}
    )

    documents = retriever.invoke(
        "You are a narrative generator for a procedural RPG game. Retrieve the most relevant documents to create a context."
    )

    state["retrieved_documents"] = documents  # Temporary (just for logging)

    if (len(documents)) > 0:
        state[cast(str, f"{state['context_type']}_context")] = "\n".join(
            [doc.page_content for doc in documents]
        )
    else:
        state[cast(str, f"{state['context_type']}_context")] = ""

    return state


# ------------------------------------------------------------------ #
#                            Graph builder                           #
# ------------------------------------------------------------------ #


def build_context_graph():
    graph = StateGraph(State)
    graph.add_node("respond", RunnableLambda(get_context_docs_from_collection))
    graph.set_entry_point("respond")
    graph.add_edge("respond", END)
    return graph.compile()
