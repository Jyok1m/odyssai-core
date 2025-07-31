import chromadb
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph, END
from langsmith import traceable
from typing_extensions import TypedDict, Required, NotRequired
from ..utils.prompt_truncation import truncate_structured_prompt
from ..config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from uuid import uuid4

# Initialize static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_TOTAL_TOKENS = 60_000
RESERVED_FOR_OUTPUT = 10_000
MAX_INPUT_TOKENS = MAX_TOTAL_TOKENS - RESERVED_FOR_OUTPUT


# State
class State(TypedDict):
    story_directives: Required[str]  # World description to induce the generation
    world_name: Required[str]
    world_id: NotRequired[str]
    llm_response: NotRequired[str]


# ------------------------------------------------------------------ #
#                              Functions                             #
# ------------------------------------------------------------------ #


@traceable(name="get_world_id")
def get_world_id(state: State) -> State:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )

    result = db_collection.get(where={"world_name": state["world_name"]})

    if len(result["metadatas"]) > 0:
        state["world_id"] = result["metadatas"][0]["world_id"]
    else:
        state["world_id"] = str(uuid4())

    return state


def create_world(state: State) -> State:
    prompt_template = """
    ## ROLE
    You are a narrative generator for a procedural RPG game.

    ## OBJECTIVE
    Your task is to generate an overview of the world "{{world_name}}".

    ## RULES
    You must respect the following directives:
    {{story_directives}}

    ## FORMAT
    Return a single valid python dictionary. 
    Each value must respect the passed directives.
    Respect the following dictionary structure:

    {
        "page_content": "string (short descriptive paragraph introducing the world)",
        "metadata": {
            "world_name": {{world_name}},
            "world_id": {{world_id}},
            "genre": "string (e.g. 'fantasy', 'sci-fi', 'dark fantasy' etc...)",
            "technology_level": "string (e.g. 'medieval', 'steampunk', 'futuristic' etc...)",
            "dominant_species": "string (e.g. 'humans', 'elves', 'androids' etc...)",
            "governance": "string (e.g. 'monarchy', 'anarchy', 'federation' etc...)",
            "magic_presence": "boolean (whether magic exists in the world)",
            "visible_in_game": "boolean (whether the player can access this world profile)"
        }
    }

    Do not include any explanations, comments, or markdown formatting.
    """

    truncated_prompt = truncate_structured_prompt(prompt_template)
    prompt = PromptTemplate.from_template(truncated_prompt, template_format="jinja2")
    formatted_prompt = prompt.format(**state)
    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        streaming=False,
        max_retries=2,
    )

    llm_response = llm_model.invoke(truncated_prompt).content
    state["llm_response"] = str(llm_response) if llm_response else ""
    print(state["llm_response"])
    return state


# ------------------------------------------------------------------ #
#                            Graph builder                           #
# ------------------------------------------------------------------ #


def world_creation_graph():
    graph = StateGraph(State)
    graph.add_node("get_world_id", RunnableLambda(get_world_id))
    graph.set_entry_point("get_world_id")
    graph.add_node("create_world", RunnableLambda(create_world))
    graph.add_edge("get_world_id", "create_world")
    graph.add_edge("create_world", END)
    return graph.compile()
