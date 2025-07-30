import os
from .workflows.context_graph import build_context_graph


def main():
    print("Welcome to Odyssai Core v0.1.0 \n")

    def get_context():
        context_type = "lore"
        os.environ["LANGCHAIN_PROJECT"] = f"odyssai-{context_type}-context"
        graph = build_context_graph()

        result = graph.invoke(
            {
                "world_id": "a137b189-2dd6-4e30-90b6-f272c1395f01",
                "context_type": context_type,
            }
        )
        print(f"Documents ({len(result['retrieved_documents'])}) : \n")
        print(result["retrieved_documents"])
        print("\n")
        print("Combined résumé : \n")
        print(result[f"{context_type}_context"])

    get_context()


if __name__ == "__main__":
    main()
