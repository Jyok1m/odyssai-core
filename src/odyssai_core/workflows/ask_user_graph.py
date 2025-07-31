# Import libs
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict, Literal, NotRequired

# Imports modules
from ..constants.prompt_questions import WORLD_BULDING_QUESTIONS


TTS_ENABLED = True

# TODO: À instancier plus tard et à inclure dans les fonctions
# tts_tool: google tts
# whisper_stt: whisper

# ------------------------------------------------------------------ #
#                            SHARED STATE                            #
# ------------------------------------------------------------------ #


class QuestionState(TypedDict):
    # Optional as inputs:
    responses: NotRequired[dict[str, str]]
    current_question: NotRequired[str]
    question_index: NotRequired[int]


# ------------------------------------------------------------------ #
#                              FUNCTIONS                             #
# ------------------------------------------------------------------ #


def ask_question(state: QuestionState) -> QuestionState:
    """Function to a ask a question to the player based on a list of dict with format [{ "key": "value" }]."""

    q_index = state.get("question_index", 0)
    question = WORLD_BULDING_QUESTIONS[q_index]["value"]

    print(f"Q: {question}")
    return {**state, "current_question": question}


def collect_answer(state: QuestionState) -> QuestionState:
    """Function to collect the input from the player and add the response to a dict collector."""

    response = input("A: ").strip()

    q_index = state.get("question_index", 0)
    key = WORLD_BULDING_QUESTIONS[q_index]["key"]

    state_responses = state.get("responses", {})
    state_responses[key] = response

    return {
        **state,
        "responses": state_responses,
        "current_question": "",
        "question_index": q_index + 1,
    }


def should_continue(state: QuestionState) -> Literal["__continue__", "__end__"]:
    """Function to determine whether the QA session reaches the total length of the questions."""

    q_index = state.get("question_index", 0)

    if q_index >= len(WORLD_BULDING_QUESTIONS):
        return "__end__"
    else:
        return "__continue__"


# ------------------------------------------------------------------ #
#                                GRAPH                               #
# ------------------------------------------------------------------ #

builder = StateGraph(QuestionState)

builder.add_node("ask", ask_question)
builder.add_node("collect", collect_answer)

builder.set_entry_point("ask")
builder.add_edge("ask", "collect")
builder.add_conditional_edges(
    "collect", should_continue, {"__continue__": "ask", "__end__": END}
)

ask_user_graph = builder.compile()
