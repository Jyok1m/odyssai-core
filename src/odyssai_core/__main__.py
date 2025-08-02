from .config import settings  # noqa: F401
from .workflows.main_graph import main_graph
# from .workflows.ask_user_graph import ask_user_graph, QuestionState
# from .workflows.world_graph import world_creation_graph
# from .workflows.lore_graph import lore_graph


def main():
    print("\n Welcome to Odyssai. Let the adventure begin!")
    result = main_graph.invoke({})
    print("Result: \n", result)

    # Ask user for inputs about the world
    # result_1 = ask_user_graph.invoke({"query_type": "init"})
    # user_answers: QuestionState = result_1["responses"]

    # # Generate the world based on the user inputs
    # result_2 = world_creation_graph.invoke(
    #     {
    #         "world_name": user_answers.get("world_name", ""),
    #         "story_directives": user_answers.get("story_directives", ""),
    #         "world_setting": user_answers.get("world_setting", ""),
    #     }
    # )

    # # Create the lore
    # result_3 = lore_graph.invoke({"world_id": result_2["world_id"]})


if __name__ == "__main__":
    main()
