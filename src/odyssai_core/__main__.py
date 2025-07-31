import os
from .workflows.ask_user_graph import ask_user_graph, QuestionState
from .workflows.world_graph import world_creation_graph
from .workflows.context_graph import build_context_graph


def generate_world():
    # Ask user for inputs about the world
    result_1 = ask_user_graph.invoke({})
    user_answers: QuestionState = result_1["responses"]

    # Generate the world based on the user inputs
    result_2 = world_creation_graph.invoke(
        {
            "world_name": user_answers.get("world_name", ""),
            "story_directives": user_answers.get("story_directives", ""),
            "world_setting": user_answers.get("world_setting", ""),
        }
    )
    world_creation_result = result_2["llm_json"]
    print(world_creation_result)


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

    # get_context()
    generate_world()


if __name__ == "__main__":
    main()
