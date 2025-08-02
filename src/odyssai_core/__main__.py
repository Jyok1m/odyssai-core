import textwrap
from .config import settings  # noqa: F401
from .workflows.main_graph import main_graph, TERMINAL_WIDTH


def main():
    cue = (
        "Welcome to Odyssai. Start by answering a few questions and let's get started!"
    )
    print("\n")
    print(textwrap.fill(f"AI: {cue}", width=TERMINAL_WIDTH))

    main_graph.invoke({})


if __name__ == "__main__":
    main()
