from .config import settings  # noqa: F401
from .workflows.main_graph import main_graph


def main():
    main_graph.invoke({}, config={"recursion_limit": 9999})


if __name__ == "__main__":
    main()
