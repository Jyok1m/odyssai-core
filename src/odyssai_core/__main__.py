import textwrap
from .config import settings  # noqa: F401
from .workflows.main_graph import main_graph, TERMINAL_WIDTH
from .utils.audio_session import recorder  # noqa: F401


def main():
    cue = (
        "Welcome to Odyssai. Start by answering a few questions and let's get started!"
    )
    print("\n")
    print(textwrap.fill(f"AI: {cue}", width=TERMINAL_WIDTH))

    # print("\n")
    # input("AI: 🟢 Press Enter to START recording...")
    # recorder.start()

    # input("")
    # audio_path = recorder.stop()

    # print("\n")
    # print(f"Audio recorded and saved to: {audio_path}")

    main_graph.invoke({}, config={"recursion_limit": 9999})


if __name__ == "__main__":
    main()
