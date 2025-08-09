from odyssai_core.config import settings  # noqa: F401
from odyssai_core.workflows.main_graph import main_graph


def main():
    main_graph.invoke(
        {
            "source": "cli",
        },
        config={"recursion_limit": 9999},
    )


if __name__ == "__main__":
    main()
