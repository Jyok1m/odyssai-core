import os
from .workflows.ask_user_graph import ask_user_graph
from .workflows.context_graph import build_context_graph
# from .workflows.world_graph import world_creation_graph


def generate_world():
    # Ask user for inputs about the world
    result_1 = ask_user_graph.invoke({})
    print(result_1)


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

    # def generate_world():
    #     os.environ["LANGCHAIN_PROJECT"] = "odyssai-world-creation"
    #     graph = world_creation_graph()

    #     result = graph.invoke(
    #         {"story_directives": "Cypberpunk universe.", "world_name": "Elysia"}
    #     )
    #     return result
    #     # print(result)

    # get_context()
    generate_world()


if __name__ == "__main__":
    main()
