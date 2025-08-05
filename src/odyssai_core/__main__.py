from .config import settings  # noqa: F401
from .workflows.main_graph import (
    main_graph,
    TERMINAL_WIDTH,
    play_text_using_google_tts,
    type_print,
)


def main():
    cue = (
        "Welcome to Odyssai. Start by answering a few questions and let's get started!"
    )
    print("\n")
    play_text_using_google_tts(cue)
    type_print(f"AI: {cue}", width=TERMINAL_WIDTH)

    main_graph.invoke({}, config={"recursion_limit": 9999})


if __name__ == "__main__":
    main()
