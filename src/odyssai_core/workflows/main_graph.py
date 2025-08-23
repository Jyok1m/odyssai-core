# Libs
import chromadb
import random
import ast
import textwrap
import shutil
import subprocess
import time
import threading
from uuid import uuid4
from datetime import datetime
from typing_extensions import TypedDict, Literal, NotRequired

# Langchain
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langsmith import traceable

# Modules
from odyssai_core.utils.google_tts import text_to_speech
from odyssai_core.utils.whisper import transcribe_audio
from odyssai_core.utils.audio_session import recorder
from odyssai_core.utils.prompt_truncation import truncate_structured_prompt
from odyssai_core.config.settings import CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE
from odyssai_core.constants.llm_models import LLM_NAME, LLM_NAME_THINKING, EMBEDDING_MODEL

# Static variables
CHROMA_DB_CLIENT = chromadb.CloudClient(CHROMA_TENANT, CHROMA_DATABASE, CHROMA_API_KEY)
TERMINAL_WIDTH = shutil.get_terminal_size((80, 20)).columns
VOICE_MODE_ENABLED = False
MAIN_TEMP = 1

# ------------------------------------------------------------------ #
#                                SCHEMA                              #
# ------------------------------------------------------------------ #


class StateSchema(TypedDict):
    source: Literal["cli", "api"]

    # User preferences
    user_language: NotRequired[str]  # 'fr' or 'en', default 'en'

    # Init Data
    world_genre: NotRequired[str]
    story_directives: NotRequired[str]
    create_new_world: NotRequired[bool]
    must_restart_init: NotRequired[bool]
    user_input: NotRequired[str]

    # World Data
    world_id: NotRequired[str]
    world_name: NotRequired[str]
    llm_generated_data: NotRequired[
        list[dict[str, str]]
    ]  # Swap data for better handling
    active_step: NotRequired[
        Literal[
            "world_creation",
            "lore_generation",
            "character_creation",
            "summary_generation",
        ]
    ]

    # Global Data
    world_context: NotRequired[str]
    lore_context: NotRequired[str]
    character_context: NotRequired[str]
    event_context: NotRequired[str]
    world_summary: NotRequired[str]

    # Gameplay Data
    ai_question: NotRequired[str]
    continue_story: NotRequired[bool]

    # Audio Data
    audio_path: NotRequired[str]

    # Character Data
    create_new_character: NotRequired[bool]
    character_id: NotRequired[str]
    character_name: NotRequired[str]
    character_gender: NotRequired[str]
    character_description: NotRequired[str]
    must_restart_character: NotRequired[bool]
    player_answer: NotRequired[str]
    immediate_events: NotRequired[str]


# ------------------------------------------------------------------ #
#                       INTERNATIONALIZATION UTILS                    #
# ------------------------------------------------------------------ #


def get_user_language(state: StateSchema) -> str:
    """Get user language from state, default to 'en'"""
    return state.get("user_language", "en")


def get_i18n_text(state: StateSchema, key: str) -> str:
    """Get internationalized text based on user language"""
    language = get_user_language(state)

    # Text mappings for different languages
    texts = {
        # Character details prompts
        "ask_character_gender": {
            "en": "What is your character's gender?",
            "fr": "Quel est le genre de votre personnage ?",
        },
        "ask_character_description": {
            "en": "What is your character's description?",
            "fr": "Quelle est la description de votre personnage ?",
        },
        # Generation cues
        "generating_world_data": {
            "en": "I am generating the data for your new world. This may take a few moments, please be patient...",
            "fr": "Je génère les données pour votre nouveau monde. Cela peut prendre quelques instants, veuillez patienter...",
        },
        "generating_character_data": {
            "en": "I am generating your character data. This may take a few moments, please be patient...",
            "fr": "Je génère les données de votre personnage. Cela peut prendre quelques instants, veuillez patienter...",
        },
        "generating_lore_data": {
            "en": "I am now imagining an additional layer of depth to the lore. This may take a few moments, please be patient...",
            "fr": "J'imagine maintenant une couche supplémentaire de profondeur pour le lore. Cela peut prendre quelques instants, veuillez patienter...",
        },
        "summarizing_story": {
            "en": "I am now summarizing your story. This may take a few moments, please be patient...",
            "fr": "Je résume maintenant votre histoire. Cela peut prendre quelques instants, veuillez patienter...",
        },
        # Continue/stop prompt
        "ask_continue": {
            "en": "Do you wish to continue? Respond by typing 'yes' or 'no'.",
            "fr": "Souhaitez-vous continuer ? Répondez en tapant 'oui' ou 'non'.",
        },
        # Input missing
        "input_missing": {
            "en": "It seems you haven't provided any input. Let's try again.",
            "fr": "Il semble que vous n'ayez rien saisi. Essayons à nouveau.",
        },
        # Welcome messages
        "welcome": {
            "en": "Welcome to Odyssai. Start by answering a few questions and let's get started! Do you want to create a new world? Respond by typing 'yes' or 'no'.",
            "fr": "Bienvenue dans Odyssai. Commençons par répondre à quelques questions ! Voulez-vous créer un nouveau monde ? Répondez en tapant 'oui' ou 'non'.",
        },
        # World creation
        "ask_world_name_create": {
            "en": "What would you like to name your new world?",
            "fr": "Comment voulez-vous nommer votre nouveau monde ?",
        },
        "ask_world_name_join": {
            "en": "What's the name of the world you'd like to join?",
            "fr": "Quel est le nom du monde que vous souhaitez rejoindre ?",
        },
        "world_exists_error": {
            "en": "This world already exists. Please choose a different name or join the existing world.",
            "fr": "Ce monde existe déjà. Veuillez choisir un autre nom ou rejoindre le monde existant.",
        },
        "world_not_found": {
            "en": "This world doesn't exist. Would you like to create it?",
            "fr": "Ce monde n'existe pas. Voulez-vous le créer ?",
        },
        # World details
        "ask_world_genre": {
            "en": "Describe the world's main genre. Give as much detail as you would like.",
            "fr": "Décrivez le genre principal du monde. Donnez autant de détails que vous le souhaitez.",
        },
        "ask_story_directives": {
            "en": "Are there particular themes or narrative threads you'd like to explore? Let your imagination guide the story's soul.",
            "fr": "Y a-t-il des thèmes ou des fils narratifs particuliers que vous aimeriez explorer ? Laissez votre imagination guider l'âme de l'histoire.",
        },
        # Character creation
        "ask_new_character": {
            "en": "Do you want to play as a new character? Respond by typing 'yes' or 'no'.",
            "fr": "Voulez-vous jouer un nouveau personnage ? Répondez en tapant 'oui' ou 'non'.",
        },
        "ask_character_name_create": {
            "en": "What would you like to name your new character?",
            "fr": "Comment voulez-vous nommer votre nouveau personnage ?",
        },
        "ask_character_name_join": {
            "en": "What's the name of the character you'd like to play?",
            "fr": "Quel est le nom du personnage que vous souhaitez jouer ?",
        },
        # Errors
        "character_exists_error": {
            "en": "This character already exists in this world. Please choose a different name.",
            "fr": "Ce personnage existe déjà dans ce monde. Veuillez choisir un autre nom.",
        },
        "character_not_found": {
            "en": "This character doesn't exist in this world. Would you like to create it?",
            "fr": "Ce personnage n'existe pas dans ce monde. Voulez-vous le créer ?",
        },
    }

    return texts.get(key, {}).get(language, texts.get(key, {}).get("en", ""))


def get_multilingual_rag_query(state: StateSchema, query_type: str, **kwargs) -> str:
    """Generate multilingual RAG queries based on user language"""
    language = get_user_language(state)

    queries = {
        "lore_search": {
            "en": f"Lore about the world {kwargs.get('world_name', 'Unknown World')}",
            "fr": f"Histoire et traditions du monde {kwargs.get('world_name', 'Monde Inconnu')}",
        },
        "story_events": {
            "en": "Most recent in-world actions/events for the player. Short factual mentions, no summaries.",
            "fr": "Événements/Actions les plus récents vécus par le joueur. Mentions factuelles courtes, sans résumé.",
        },
        "character_context": {
            "en": f"Information about characters in world {kwargs.get('world_name', 'Unknown World')}",
            "fr": f"Informations sur les personnages du monde {kwargs.get('world_name', 'Monde Inconnu')}",
        },
    }

    return queries.get(query_type, {}).get(
        language, queries.get(query_type, {}).get("en", "")
    )


def get_multilingual_llm_prompt(state: StateSchema, prompt_type: str, **kwargs) -> str:
    """Generate multilingual LLM prompts based on user language"""
    language = get_user_language(state)

    prompts = {
        # Lore generation
        "lore_generation": {
            "en": """
            ## ROLE
            You are a storyteller for a procedural RPG game.  
            You write exciting and mysterious background stories that make the game world "{{world_name}}" feel alive and full of secrets.

            ## OBJECTIVE
            Your job is to write one rich, standalone paragraph of lore about the world "{{world_name}}" (in normal case).  
            The text should feel like it comes from an old forgotten book, a story told around a campfire, or an important piece of the world's hidden history.  
            Use simple words and expressions so that a 15-year-old teenager can understand everything.

            ## EXISTING CONTEXTS
            Here is information about the world to help guide your story:

            --- WORLD CONTEXT ---
            {{world_context}}
            ----------------------

            Here is lore that already exists for this world:

            --- EXISTING LORE CONTEXT ---
            {{lore_context}}
            -----------------------------

            Here is character information that already exists for this world:

            --- EXISTING CHARACTER CONTEXT ---
            {{character_context}}
            -----------------------------

            ## FORMAT
            - Write only one detailed paragraph of lore in normal language.
            - Do not explain the story or add comments about it.
            - Do not use markdown, bullet points, or code formatting.
            - Give the answer as a raw Python dictionary exactly like this:

            {
                "page_content": "string" (a rich lore paragraph that adds to the world's story or history),
                "metadata": {
                    "world_name": "{{world_name}}" (in lowercase),
                    "world_id": "{{world_id}}",
                    "type": "lore",
                    "theme": "based on world context",
                    "tags": "string listing the main themes or ideas" (e.g. 'ancient prophecy, lost kingdom, great battle')
                }
            }

            !!! DO NOT USE MARKDOWN OR FORMATTING LIKE ```python. OUTPUT ONLY A RAW PYTHON DICTIONARY. !!!
            """,
            "fr": """
            ## RÔLE
            Tu es un conteur pour un jeu RPG procédural.  
            Tu écris des histoires de fond passionnantes et mystérieuses qui rendent le monde "{{world_name}}" vivant et plein de secrets.

            ## OBJECTIF
            Ton travail est d'écrire un paragraphe autonome et riche de lore sur le monde "{{world_name}}" (en casse normale).  
            Le texte doit donner l'impression de venir d'un vieux livre oublié, d'une histoire racontée autour d'un feu de camp, ou d'un morceau important de l'histoire cachée du monde.  
            Utilise des mots et expressions simples pour qu'un adolescent de 15 ans comprenne tout.

            ## CONTEXTES EXISTANTS
            Voici des informations sur le monde pour guider ton histoire :

            --- CONTEXTE DU MONDE ---
            {{world_context}}
            -------------------------

            Voici le lore qui existe déjà pour ce monde :

            --- CONTEXTE DU LORE EXISTANT ---
            {{lore_context}}
            ---------------------------------

            Voici les informations sur les personnages existants pour ce monde :

            --- CONTEXTE DES PERSONNAGES EXISTANTS ---
            {{character_context}}
            -----------------------------------------

            ## FORMAT
            - Écris un seul paragraphe détaillé de lore en langage normal.
            - N'explique pas l'histoire et n'ajoute pas de commentaires.
            - N'utilise pas de markdown, de puces ou de formatage de code.
            - Donne la réponse sous forme d'un dictionnaire Python brut exactement comme ceci :

            {
                "page_content": "string" (un paragraphe de lore riche qui ajoute à l'histoire ou au passé du monde),
                "metadata": {
                    "world_name": "{{world_name}}" (en minuscules),
                    "world_id": "{{world_id}}",
                    "type": "lore",
                    "theme": "basé sur le contexte du monde",
                    "tags": "liste des thèmes ou idées principaux sous forme de chaîne de caractères !!!" (ex. 'prophétie ancienne, royaume perdu, grande bataille')
                }
            }

            !!! N'UTILISE PAS DE MARKDOWN OU DE FORMATAGE COMME ```python. SORTIE UNIQUEMENT UN DICTIONNAIRE PYTHON BRUT. !!!
            """,
        },
        # World summary
        "world_summary": {
            "en": """
            ## ROLE
            You are a world narrator for a procedural RPG game.  
            You tell the story of the world "{{world_name}}" in a simple, clear way.

            ## OBJECTIVE
            Write a short and immersive summary of "{{world_name}}".  
            It will be used:
            - At the start of the game to introduce the story,
            - At any time to remind players what has happened,
            - As an easy reference for players who may not speak English well.  

            Use simple words and expressions so a 15-year-old teenager can understand everything.

            ## INPUT CONTEXTS

            --- WORLD CONTEXT ---
            {{world_context}}

            --- LORE CONTEXT ---
            {{lore_context}}

            --- CHARACTER CONTEXT ---
            {{character_context}}

            ## STYLE & CONSTRAINTS
            - Use clear and easy-to-read language for non-native English speakers.
            - Summarize the main points of the world's story, history, events, and characters so far.
            - Avoid poetic or overly complicated language.
            - Keep names and sentences simple.
            - Tone should be neutral and informative, but still engaging.
            - You must talk directly to the player (use "you").
            - Do not include markdown, YAML, code blocks, or bullet points.

            ## FORMAT
            Return a **single raw string** of one or two short paragraphs (max ~100 words each) covering:
            - The current state and setting of the world
            - Key events that have happened so far
            - Any important characters or recent developments

            !!! DO NOT USE MARKDOWN, YAML, OR FORMATTING. OUTPUT ONLY A RAW STRING. !!!
            """,
            "fr": """
            ## RÔLE
            Tu es un narrateur de monde pour un jeu RPG procédural.  
            Tu racontes l'histoire du monde "{{world_name}}" de façon simple et claire.

            ## OBJECTIF
            Rédige un résumé court et immersif de "{{world_name}}".  
            Il sera utilisé :
            - Au début du jeu pour introduire l'histoire,
            - À tout moment pour rappeler aux joueurs ce qui s'est passé,
            - Comme référence facile pour les joueurs qui ne parlent pas bien anglais.  

            Utilise des mots et expressions simples pour qu'un adolescent de 15 ans comprenne tout.

            ## CONTEXTES D'ENTRÉE

            --- CONTEXTE DU MONDE ---
            {{world_context}}

            --- CONTEXTE DU LORE ---
            {{lore_context}}

            --- CONTEXTE DES PERSONNAGES ---
            {{character_context}}

            ## STYLE & CONTRAINTES
            - Utilise un langage clair et facile à lire pour les non-anglophones.
            - Résume les points principaux de l'histoire, du passé, des événements et des personnages du monde jusqu'à présent.
            - Évite le langage poétique ou trop compliqué.
            - Garde les noms et les phrases simples.
            - Le ton doit être neutre et informatif, mais engageant.
            - Tu dois absolument t'adresser directement au joueur (utilise "tu").
            - N'inclus pas de markdown, YAML, blocs de code ou puces.

            ## FORMAT
            Donne une **seule chaîne brute** d'un ou deux paragraphes courts (max ~100 mots chacun) couvrant :
            - L'état et le décor actuels du monde
            - Les événements clés qui se sont produits jusqu'à présent
            - Les personnages ou développements importants récents

            !!! N'UTILISE PAS DE MARKDOWN, YAML OU DE FORMATAGE. SORTIE UNIQUEMENT UNE CHAÎNE BRUTE. !!!
            """,
        },
        # Immediate event summary
        "immediate_event_summary": {
            "en": """
        ## ROLE
        You summarize only what the player just did and what immediately happened next.

        ## OBJECTIVE
        Write a short, direct recap for the player in simple language. Prefer a single paragraph (2–4 sentences, ≤ ~80 words). Use a second short paragraph only if the action and consequence are clearly distinct. Never exceed ~120 words total.

        ## INPUTS
        --- EVENT CONTEXT ---
        {{event_context}}
        --- PLAYER ACTION ---
        {{player_answer}}

        ## RULES
        - Focus strictly on the most recent player action and its immediate outcome.
        - If speaker labels like "AI:" or "Player:" appear, ignore them and extract the latest action/outcome.
        - Do not add lore, backstory, motivations, or new facts.
        - Speak directly to the player using "you".
        - Keep vocabulary simple and sentences short (max ~20 words).
        - No lists, quotes, markdown, YAML, or code blocks. No meta commentary.

        ## OUTPUT
        Return a single raw string (one short paragraph; optionally two if needed) that tells:
        1) What you just did. 2) What happened right after.

        If both inputs are empty or unclear, say: "You are ready to act, but nothing has happened yet."

        !!! DO NOT USE MARKDOWN, YAML, OR ANY FORMATTING. OUTPUT ONLY A RAW STRING. !!!
        """,
            "fr": """
        ## RÔLE
        Tu résumes uniquement ce que le joueur vient de faire et ce qui s’est passé juste après.

        ## OBJECTIF
        Rédige un rappel court et direct pour le joueur, en langage simple. Privilégie un seul paragraphe (2–4 phrases, ≤ ~80 mots). Utilise un deuxième court paragraphe seulement si l’action et la conséquence sont clairement distinctes. Ne dépasse jamais ~120 mots au total.

        ## ENTRÉES
        --- CONTEXTE DE L’ÉVÉNEMENT ---
        {{event_context}}
        --- ACTION DU JOUEUR ---
        {{player_answer}}

        ## RÈGLES
        - Concentre-toi strictement sur la dernière action du joueur et sa conséquence immédiate.
        - Si des libellés comme "AI:" ou "Player:" apparaissent, ignore-les et extrais la dernière action/conséquence.
        - N’ajoute ni lore, ni contexte, ni faits nouveaux.
        - Adresse-toi directement au joueur avec "tu".
        - Vocabulaire simple, phrases courtes (max ~20 mots).
        - Pas de listes, de citations, de markdown, de YAML, ni de blocs de code. Aucune méta.

        ## SORTIE
        Retourne une seule chaîne brute (un paragraphe court ; deux au maximum si nécessaire) qui dit :
        1) Ce que tu viens de faire. 2) Ce qui s’est passé juste après.

        Si les entrées sont vides ou ambiguës, dis : "Tu es prêt à agir, mais rien ne s’est encore passé."

        !!! N’UTILISE PAS DE MARKDOWN, YAML OU DE FORMATAGE. RENDS UNIQUEMENT UNE CHAÎNE BRUTE. !!!
        """,
        },
        # Next prompt
        "next_prompt": {
        "en": """
        ## ROLE
        You are a grounded, realistic game narrator.

        ## OBJECTIVE
        Using the rules below, continue the scene in a clear, practical way so the player can choose their next action.

        ## DECISION LOGIC
        - IF --- RECENT EVENTS in Descending Order --- is non-empty:
        * Continue **directly** from the last player action and its immediate consequence.
        * Make the story progress according to the player's actions.
        * The events are: {{event_context}}
        - ELSE:
        * Start in a plausible location for {{character_name}} within {{world_context}} / {{lore_context}}.
        * Give one immediate goal and a small, concrete obstacle.
        - Priority of sources: RECENT EVENTS > CHARACTER CONTEXT > WORLD/LORE. Use only what is needed.

        ## ACTION RESOLUTION RULE
        - Treat the last player action as **already performed**.
        - Place the player **in the resulting location**.

        ## PROGRESSION & ANTI-LOOP RULES
        - **State mutation every turn:** change at least one concrete element (e.g., door now open/locked, corridor flooded to ankle-deep, light level reduced, NPC moved, heat source cooled).
        - **Consume or retire affordances:** if an exit/object is used or inspected, mark it as **resolved** and do not offer it again unless circumstances changed (e.g., now powered, now flooded).
        - **Choice novelty:** do **not** repeat either of the previous turn’s options unless their state changed meaningfully; avoid generic directions ("go left/right", "go deeper").
        - **No soft resets:** never reintroduce a corridor fork if we already resolved it; never bounce back to vague exploration.

        ## CHOICE RULE
        - End with **one** question giving **exactly two** realistic, mutually exclusive actions available **here and now**, each tied to a specific affordance in the current scene.

        ## REALISM RULES
        - Prefer plain, observable facts (sight, sound, objects, distances, time, risks). Use cause → effect.
        - Avoid vague mysticism/prophecy language: ethereal, destiny, whispers of, mysterious embrace, ancient call, enigmatic, otherworldly.
        - Sentences ≈ 8–18 words; limit adjectives; no metaphors.
        - If magic/tech exists, describe it operationally (what it does now, constraints, costs).

        ## CONTEXT
        The player plays as: {{character_name}}.

        --- RECENT EVENTS (in Descending Order) ---
        {{event_context}}

        --- WORLD CONTEXT ---
        {{world_context}}

        --- LORE CONTEXT ---
        {{lore_context}}

        --- CHARACTER CONTEXT ---
        {{character_context}}

        --- SCENE STATE (authoritative; provide if available) ---
        {{scene_state}}
        (If empty, derive a minimal state from the latest event: location_id; timeframe; light/visibility; environment; exits[] with id/label/status; goals; resources; hazards/progress_clock; visited[].)

        ## OUTPUT FORMAT
        - One compact paragraph in plain text, present tense, addressing the player as "you".
        - Include a specific, immediate situation with concrete constraints (light, visibility, footing, noise, time/resource pressure).
        - End with a clear, actionable question offering two realistic options tied to **present** affordances.
        - Do not recap beyond the latest event. No lists or meta commentary.

        !!! DO NOT INCLUDE MARKDOWN OR CODE FORMATTING !!!

        ## EXAMPLES (imitate style; do not copy content)
        - Example A — Events present; you are already **in the room**; irreversible change applied:
        You stand in the central chamber. Warm air vents hum and the runes give steady amber light; you see about five meters. The door you used swings shut and latches from the other side; returning that way is no longer possible (flooding 1/4). To your right, a hatch marked with a drain symbol is now unlocked; ahead, an altar panel pulses and throws mild heat. Do you pull the drain hatch to access the wash alcove or inspect the altar panel for a power control?

        - Example B — No events; start with goal, obstacle, and a ticking clock:
        You reach a service landing under a coral arch. Light flickers and the floor is slick; your boots squeak on wet stone. A beacon marks a maintenance tunnel, but the grate is jammed; the stairwell climbs toward faint airflow (tide 2/5). Your goal is to reach shelter before the next surge. Do you lever the grate with a loose rung to enter the tunnel or climb the stairs to reach the vented platform?
        """,




        "fr": """## RÔLE
        Tu es un narrateur réaliste et concret.

        ## OBJECTIF
        En suivant les règles ci-dessous, poursuis la scène de façon claire et pratique pour que le joueur choisisse sa prochaine action.

        ## LOGIQUE DE DÉCISION
        - SI --- ÉVÉNEMENTS RÉCENTS dans l'ordre descendant --- n’est pas vide :
        * Enchaîne **directement** sur la dernière action du joueur et sa conséquence immédiate.
        * Fais progresser l'histoire en fonction des actions du joueur.
        * Les événements sont : {{event_context}}
        - SINON :
        * Démarre dans un lieu crédible pour {{character_name}} au sein de {{world_context}} / {{lore_context}}.
        * Donne un objectif immédiat et un petit obstacle concret.
        - Priorité des sources : ÉVÉNEMENTS RÉCENTS > CONTEXTE PERSONNAGE > MONDE/LORE. N’utilise que le nécessaire.

        ## RÈGLE D’ENCHAÎNEMENT
        - Considère la dernière action du joueur comme **déjà effectuée**.
        - Place le joueur **dans le lieu résultant**.

        ## PROGRESSION & ANTI-BOUCLE
        - **Mutation d’état à chaque tour** : modifie au moins un élément concret (porte ouverte/verrouillée, couloir à mi-jambe d’eau, baisse de luminosité, déplacement d’un son/PNJ, source de chaleur qui faiblit).
        - **Consommation des affordances** : si une issue/objet est utilisé ou inspecté, marque-le **résolu** et ne le repropose pas sauf changement réel (ex. alimenté désormais, désormais inondé).
        - **Nouveauté des choix** : ne répète **aucune** des deux options du tour précédent, sauf si leur état a **vraiment** changé ; évite les directions génériques (« aller à gauche/droite », « aller plus loin »).
        - **Pas de reset mou** : ne réintroduis pas une fourche déjà résolue ; ne reviens pas à une exploration vague.

        ## RÈGLE DE CHOIX
        - Termine par **une** question proposant **exactement deux** actions réalistes, exclusives, faisables **ici et maintenant**, chacune liée à une affordance précise de la scène.

        ## RÈGLES DE RÉALISME
        - Faits observables (visuel, sons, objets, distances, temps, risques). Chaîne cause → effet.
        - Évite le mysticisme/texte prophétique : éthéré, destinée, murmures de…, étreinte mystérieuse, énigmatique, d’un autre monde.
        - Phrases de 8–18 mots ; peu d’adjectifs ; pas de métaphores.
        - Si magie/tech existe, décris-la de façon opérationnelle (ce qu’elle fait maintenant, contraintes, coûts).

        ## CONTEXTE
        Le joueur incarne : {{character_name}}.

        --- ÉVÉNEMENTS RÉCENTS (dans l'ordre descendant) ---
        {{event_context}}

        --- CONTEXTE DU MONDE ---
        {{world_context}}

        --- CONTEXTE DU LORE ---
        {{lore_context}}

        --- CONTEXTE DES PERSONNAGES ---
        {{character_context}}

        --- ÉTAT DE SCÈNE (prioritaire si fourni) ---
        {{scene_state}}
        (S’il est vide, dérive un état minimal depuis le dernier événement : location_id ; instant ; lumière/visibilité ; environnement ; issues[] avec id/libellé/statut ; objectifs ; ressources ; dangers/compteur ; visited[].)

        ## FORMAT DE SORTIE
        - Un seul paragraphe concis, au présent, en t’adressant au joueur avec « tu ».
        - Inclure une situation immédiate avec contraintes concrètes (lumière, visibilité, appuis, bruit, pression temps/ressources).
        - Terminer par une question claire offrant deux options réalistes liées aux **affordances présentes**.
        - Ne récapitule pas au-delà du dernier événement. Pas de listes ni de méta.

        !!! N'INCLUS PAS DE MARKDOWN OU DE FORMATAGE DE CODE !!!

        ## EXEMPLES (imiter le style, ne pas copier)
        - Exemple A — Événements présents ; tu es déjà **dans la chambre** ; changement irréversible :
        Tu es dans la chambre centrale. L’air chaud vibre et les runes éclairent à cinq mètres. La porte par laquelle tu es venu se referme et se verrouille côté opposé : retour impossible (inondation 1/4). À droite, une trappe avec symbole d’évacuation est désormais déverrouillée ; en face, un panneau d’autel pulse une chaleur régulière. Tu tires la trappe pour accéder à l’alcôve d’eau ou tu inspectes le panneau pour trouver un contrôle d’alimentation ?

        - Exemple B — Aucun événement ; but, obstacle et horloge :
        Tu atteins un palier de service sous une arche de corail. La lumière saute et le sol glisse ; tes semelles crissent sur la pierre mouillée. Un balisage indique un tunnel technique mais la grille est coincée ; l’escalier monte vers un souffle d’air (marée 2/5). Ton but est d’atteindre un abri avant la prochaine vague. Tu fais levier avec un barreau pour ouvrir la grille ou tu montes l’escalier vers la plateforme ventilée ?
        """,
        },
        
        "world_creation": {
            "en": """
            ## ROLE
            You are a world creator for a procedural RPG game.  
            You make short and vivid descriptions that help players imagine the world "{{world_name}}" (in normal case).

            ## OBJECTIVE
            Your job is to write an overview of the world "{{world_name}}".  
            The text should match the style and theme: {{world_genre}}  
            You must also follow these extra instructions: {{story_directives}}  
            Use simple words and expressions so a 15-year-old teenager can understand everything.

            ## FORMAT
            - Each detail must fit with the given theme and instructions.
            - Write in a clear and easy-to-read way.
            - Do not explain or add comments about the story.
            - Do not use markdown or special formatting.
            - Return only one valid Python dictionary.
            - Follow exactly this structure:

            {
                "page_content": string (a short paragraph introducing the world in a vivid way),
                "metadata": {
                    "world_name": "{{world_name}}" (in lowercase),
                    "genre": "string" (e.g. 'fantasy', 'sci-fi', 'dark fantasy' etc., based on {{world_genre}}),
                    "dominant_species": "string" (e.g. 'humans', 'elves', 'androids' etc.),
                    "magic_presence": Python Boolean (True or False) (if magic exists in the world),
                    "governance": "string" (e.g. 'monarchy', 'anarchy', 'federation' etc.)
                    "user_language": "{{user_language}}"
                }
            }

            !!! DO NOT USE MARKDOWN OR FORMATTING LIKE ```python. OUTPUT ONLY A RAW PYTHON DICTIONARY. !!!
            """,
            "fr": """
            ## RÔLE
            Tu es un créateur de monde pour un jeu RPG procédural.  
            Tu créées des descriptions courtes et vivantes qui aident les joueurs à imaginer le monde "{{world_name}}" (en casse normale).

            ## OBJECTIF
            Ton travail est d'écrire un aperçu du monde "{{world_name}}".  
            Le texte doit correspondre au style et au thème : {{world_genre}}  
            Tu dois aussi suivre ces instructions supplémentaires : {{story_directives}}  
            Utilise des mots et expressions simples pour qu'un adolescent de 15 ans comprenne tout.

            ## FORMAT
            - Chaque détail doit correspondre au thème et aux instructions donnés.
            - Écris de manière claire et facile à lire.
            - N'explique pas et n'ajoute pas de commentaires sur l'histoire.
            - N'utilise pas de markdown ou de formatage spécial.
            - Retourne seulement un dictionnaire Python valide.
            - Suis exactement cette structure :

            {
                "page_content": string (un court paragraphe présentant le monde de manière vivante),
                "metadata": {
                    "world_name": "{{world_name}}" (en minuscules),
                    "genre": "string" (ex. 'fantasy', 'sci-fi', 'dark fantasy' etc., basé sur {{world_genre}}),
                    "dominant_species": "string" (ex. 'humans', 'elves', 'androids' etc.),
                    "magic_presence": Booléen Python (True ou False) (si la magie existe dans le monde),
                    "governance": "string" (ex. 'monarchy', 'anarchy', 'federation' etc.)
                    "user_language": "{{user_language}}"
                }
            }

            !!! N'UTILISE PAS DE MARKDOWN OU DE FORMATAGE COMME ```python. SORTIE UNIQUEMENT UN DICTIONNAIRE PYTHON BRUT. !!!
            """,
        },
        "character_creation": {
            "en": """
            ## ROLE
            You are a character creator for a procedural RPG game.  
            You make vivid, easy-to-imagine characters who fit well into fantasy or science-fiction worlds.

            ## OBJECTIVE
            Your task is to write a detailed and engaging character profile for "{{character_name}}" based on the following:

            - Character gender: {{character_gender}}
            - Character concept or description: "{{character_description}}"
            - World name: {{world_name}}
            - World ID: {{world_id}}

            Use the world as inspiration, but focus on making the character unique and memorable, with a clear personality, role, and background.  
            Use simple words and expressions so a 15-year-old teenager can understand everything.

            ## EXISTING CONTEXTS
            Here is information about the world to help guide your thinking:

            --- WORLD CONTEXT ---
            {{world_context}}
            ----------------------

            Here is lore that already exists for this world:

            --- EXISTING LORE CONTEXT ---
            {{lore_context}}
            -----------------------------

            ## FORMAT & STYLE
            - Write one strong paragraph describing the character's past, personality traits, abilities, and role in the story.
            - Avoid overused ideas unless you twist them in an original way.
            - Keep it immersive but easy to read — like a game character codex.
            - Do NOT include markdown, YAML, or bullet points.
            - Output a single valid Python dictionary using exactly this format:

            {
                "page_content": "string" (a well-written character overview),
                "metadata": {
                    "character_name": "{{character_name}}" (in lowercase),
                    "world_id": "{{world_id}}",
                    "world_name": "{{world_name}}" (in lowercase),
                    "character_gender": "{{character_gender}}",
                    "short_description": "short summary of the character's role and personality"
                }
            }

            !!! DO NOT USE MARKDOWN OR FORMATTING LIKE ```python. OUTPUT ONLY A RAW PYTHON DICTIONARY. !!!
            """,
            "fr": """
            ## RÔLE
            Tu es un créateur de personnage pour un jeu RPG procédural.  
            Tu créées des personnages vivants et faciles à imaginer qui s'intègrent bien dans des mondes fantastiques ou de science-fiction.

            ## OBJECTIF
            Ta tâche est d'écrire un profil de personnage détaillé et captivant pour "{{character_name}}" basé sur ce qui suit :

            - Genre du personnage : {{character_gender}}
            - Concept ou description du personnage : "{{character_description}}"
            - Nom du monde : {{world_name}}
            - ID du monde : {{world_id}}

            Utilise le monde comme inspiration, mais concentre-toi sur la création d'un personnage unique et mémorable, avec une personnalité claire, un rôle et un background.  
            Utilise des mots et expressions simples pour qu'un adolescent de 15 ans comprenne tout.

            ## CONTEXTES EXISTANTS
            Voici des informations sur le monde pour guider ta réflexion :

            --- CONTEXTE DU MONDE ---
            {{world_context}}
            -------------------------

            Voici le lore qui existe déjà pour ce monde :

            --- CONTEXTE DU LORE EXISTANT ---
            {{lore_context}}
            ---------------------------------

            ## FORMAT & STYLE
            - Écris un paragraphe solide décrivant le passé du personnage, ses traits de personnalité, ses capacités et son rôle dans l'histoire.
            - Évite les idées trop utilisées sauf si tu leur donnes une tournure originale.
            - Garde-le immersif mais facile à lire — comme un codex de personnage de jeu.
            - N'inclus PAS de markdown, YAML ou de puces.
            - Sors un seul dictionnaire Python valide en utilisant exactement ce format :

            {
                "page_content": "string" (un aperçu de personnage bien écrit),
                "metadata": {
                    "character_name": "{{character_name}}" (en minuscules),
                    "world_id": "{{world_id}}",
                    "world_name": "{{world_name}}" (en minuscules),
                    "character_gender": "{{character_gender}}",
                    "short_description": "résumé court du rôle et de la personnalité du personnage"
                }
            }

            !!! N'UTILISE PAS DE MARKDOWN OU DE FORMATAGE COMME ```python. SORTIE UNIQUEMENT UN DICTIONNAIRE PYTHON BRUT. !!!
            """,
        },
    }

    return prompts.get(prompt_type, {}).get(
        language, prompts.get(prompt_type, {}).get("en", "")
    )


# ------------------------------------------------------------------ #
#                       Audio Utility Functions                      #
# ------------------------------------------------------------------ #


def transcribe_audio_file(audio_path: str) -> str:
    transcript = transcribe_audio(audio_path)
    return transcript.strip()


def play_text_using_google_tts(text: str) -> None:
    audio_path = text_to_speech(text)
    subprocess.run(["afplay", audio_path])


def type_print(text: str, delay: float = 0.05, width: int = 80) -> None:
    wrapped = textwrap.fill(text, width=width)
    for char in wrapped:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def play_and_type(cue: str, width: int = 80):
    # Lance la synthèse vocale en parallèle
    tts_thread = threading.Thread(
        target=play_text_using_google_tts, args=(cue,), daemon=True
    )
    tts_thread.start()

    # Affiche le texte progressivement
    type_print(f"AI: {cue}", width=width)


# ------------------------------------------------------------------ #
#                             OTHER UTILS                            #
# ------------------------------------------------------------------ #


def make_retriever(db_collection, where: dict[str, str]):
    mode = random.choices(["focused", "exploratory"], weights=[0.7, 0.3])[0]

    if mode == "focused":
        # peu de diversité, peu de docs
        k = random.choice([6, 8, 10])
        lambda_mult = 0.1  # proche de la similarité pure
    else:
        # plus de diversité, un peu plus de docs
        k = random.choice([8, 10, 12])
        lambda_mult = random.choice([0.5, 0.7, 0.9])

    return db_collection.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 4,
            "lambda_mult": lambda_mult,
            "where": where,
        },
    )


# ------------------------------------------------------------------ #
#                  PLAYER INPUT (VOICE OR TEXT) UTILITY              #
# ------------------------------------------------------------------ #


def get_player_answer(cue: str, force_type: bool = False) -> str:
    print("\n")
    play_and_type(cue, width=TERMINAL_WIDTH)

    if not VOICE_MODE_ENABLED or force_type:
        return input("Type in your answer: ").strip()

    # If using voice input, run the 3-step voice pipeline manually
    input("Press Enter to record")
    print("\n")
    print("AI: I am listening...")
    recorder.start()

    input("")
    audio_path = recorder.stop()
    response = transcribe_audio_file(audio_path)
    return response


# ------------------------------------------------------------------ #
#                     WORLD GENERATION FUNCTIONS                     #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Ask player if they want to create a new world")
def ask_if_new_world(state: StateSchema) -> StateSchema:
    cue = get_i18n_text(state, "welcome")
    response = get_player_answer(cue, force_type=True).lower()

    # Handle both languages for positive responses
    positive_responses = ["yes", "y", "oui", "o"]
    state["create_new_world"] = response in positive_responses
    return state


@traceable(run_type="chain", name="Ask for the name of the world")
def ask_world_name(state: StateSchema) -> StateSchema:
    if state.get("create_new_world"):
        cue = get_i18n_text(state, "ask_world_name_create")
    else:
        cue = get_i18n_text(state, "ask_world_name_join")

    world_name = get_player_answer(cue, force_type=True)
    state["world_name"] = world_name.strip().lower()
    state["user_input"] = world_name.strip()
    return state


@traceable(run_type="chain", name="Check if world exists")
def check_world_exists(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )
    result = db_collection.get(where={"world_name": state.get("world_name", "")})
    world_exists = len(result["ids"]) > 0

    if world_exists and state.get("create_new_world"):
        cue = (
            f"The world '{state.get('world_name')}' already exists. "
            "Please restart the process and choose a different name."
        )
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_init"] = True
            return state
        else:
            raise ValueError(cue)

    elif not world_exists and not state.get("create_new_world"):
        cue = (
            f"The world '{state.get('world_name')}' does not exist. "
            "You must choose a different name or create a new world."
        )
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_init"] = True
            return state
        else:
            raise ValueError("does not exist")

    state["must_restart_init"] = False
    state["create_new_world"] = not world_exists
    state["world_id"] = result["ids"][0] if result["ids"] else str(uuid4())
    return state


@traceable(run_type="chain", name="Check if world exists by id")
def check_world_exists_by_id(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )
    result = db_collection.get(ids=[state.get("world_id", "")])
    world_exists = result["ids"]

    if not world_exists:
        raise ValueError("World does not exist")
    else:
        state["world_name"] = result["metadatas"][0].get("world_name", "")
        return state


@traceable(run_type="chain", name="Check if character exists by id")
def check_character_exists_by_id(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="characters",
    )
    result = db_collection.get(ids=[state.get("character_id", "")])
    character_exists = result["ids"]

    if not character_exists:
        raise ValueError("Character does not exist")
    else:
        state["character_name"] = result["metadatas"][0].get("character_name", "")
        return state


@traceable(run_type="chain", name="Ask for the genre of the world")
def ask_world_genre(state: StateSchema) -> StateSchema:
    cue = get_i18n_text(state, "ask_world_genre")
    world_genre = get_player_answer(cue)
    state["world_genre"] = (
        world_genre.strip() if world_genre else "Choose a random genre"
    )
    return state


@traceable(run_type="chain", name="Ask for story directives")
def ask_story_directives(state: StateSchema) -> StateSchema:
    cue = get_i18n_text(state, "ask_story_directives")
    story_directives = get_player_answer(cue)
    state["story_directives"] = (
        story_directives.strip()
        if story_directives
        else "No specific directives provided."
    )
    return state


@traceable(run_type="chain", name="LLM Generate World Data")
def llm_generate_world_data(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = get_i18n_text(state, "generating_world_data")
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)

    state["active_step"] = "world_creation"

    # Get multilingual prompt template
    prompt_template = get_multilingual_llm_prompt(state, "world_creation")

    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get(
            "world_name",
            "World name not provided. Generate a default name.",
        ),
        world_genre=state.get("world_genre", "fantasy"),
        story_directives=state.get(
            "story_directives",
            "No specific directives provided. Generate a general narrative.",
        ),
        user_language=state.get("user_language", "en"),
    )
    truncated_prompt = truncate_structured_prompt(formatted_prompt)
    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    llm_dict: dict[str, str] = ast.literal_eval(llm_response)

    state["llm_generated_data"] = [llm_dict]
    state["create_new_character"] = True  # Set to True to prompt character creation
    state["world_context"] = llm_dict.get("page_content", "")
    return state


# ------------------------------------------------------------------ #
#                         CHARACTER FUNCTIONS                        #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Ask player if they want to create a new character")
def ask_create_new_character(state: StateSchema) -> StateSchema:
    cue = get_i18n_text(state, "ask_new_character")
    response = get_player_answer(cue, force_type=True).lower()
    state["create_new_character"] = response in ["yes", "y", "oui", "o"]
    return state


@traceable(run_type="chain", name="Ask for the name of the character")
def ask_new_character_name(state: StateSchema) -> StateSchema:
    if state.get("create_new_character"):
        cue = get_i18n_text(state, "ask_character_name_create")
    else:
        cue = get_i18n_text(state, "ask_character_name_join")

    character_name = get_player_answer(cue, force_type=True)
    state["character_name"] = character_name.strip().lower()
    state["user_input"] = character_name.strip()
    return state


@traceable(run_type="chain", name="Check if character exists")
def check_character_exists(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="characters",
    )
    result = db_collection.get(
        where={
            "$and": [
                {"world_id": state.get("world_id", "")},
                {"character_name": state.get("character_name", "")},
            ]
        }
    )
    character_exists = len(result["ids"]) > 0

    if character_exists and state.get("create_new_character"):
        cue = get_i18n_text(state, "character_exists_error")
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_character"] = True
            return state
        else:
            raise ValueError("does not exist")
    elif not character_exists and not state.get("create_new_character"):
        cue = get_i18n_text(state, "character_not_found")
        if state.get("source") == "cli":
            print("\n")
            play_and_type(cue, width=TERMINAL_WIDTH)
            state["must_restart_character"] = True
            return state
        else:
            raise ValueError("not found")

    state["must_restart_character"] = False
    state["create_new_character"] = not character_exists
    state["character_id"] = result["ids"][0] if result["ids"] else str(uuid4())
    return state


@traceable(run_type="chain", name="Ask for character details")
def ask_character_details(state: StateSchema) -> StateSchema:
    gender_cue = get_i18n_text(state, "ask_character_gender")
    desc_cue = get_i18n_text(state, "ask_character_description")
    character_gender = get_player_answer(gender_cue)
    character_description = get_player_answer(desc_cue)

    state["character_gender"] = (
        character_gender.strip() if character_gender else "Generate a character gender"
    )
    state["character_description"] = (
        character_description.strip()
        if character_description
        else "Generate a character description"
    )

    return state


@traceable(run_type="chain", name="LLM Generate Character Data")
def llm_generate_character_data(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = get_i18n_text(state, "generating_character_data")
        play_and_type(cue, width=TERMINAL_WIDTH)

    state["active_step"] = "character_creation"

    prompt_template = get_multilingual_llm_prompt(state, "character_creation")
    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        character_name=state.get(
            "character_name",
            "Character name not provided. Generate a default name.",
        ),
        world_id=state.get("world_id", str(uuid4())),
        world_name=state.get(
            "world_name",
            "World name not provided. Generate a default name.",
        ),
        character_gender=state.get(
            "character_gender",
            "Character gender not provided. Generate a default gender.",
        ),
        character_description=state.get(
            "character_description",
            "Character description not provided. Generate a default description.",
        ),
        world_context=state.get("world_context", "No world context available yet."),
        lore_context=state.get("lore_context", "No lore context available yet."),
    )
    truncated_prompt = truncate_structured_prompt(formatted_prompt)
    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )
    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )
    llm_dict: dict[str, str] = ast.literal_eval(llm_response)
    state["llm_generated_data"] = [llm_dict]
    state["character_context"] = llm_dict.get("page_content", "")
    return state


# ------------------------------------------------------------------ #
#                      LORE GENERATION FUNCTIONS                     #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Get world context")
def get_world_context(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )
    result = db_collection.get(ids=[state.get("world_id", "")])

    if result["ids"]:
        state["world_context"] = result["documents"][0]
    else:
        state["world_context"] = "No context provided."

    return state


@traceable(run_type="chain", name="Get all worlds list")
def get_all_worlds(lang) -> list[dict]:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="worlds",
    )

    # Get all worlds from the database
    result = db_collection.get(where={"user_language": lang})

    if not result["ids"]:
        return []

    worlds_list = []
    for i, world_id in enumerate(result["ids"]):
        world_data = {
            "world_id": world_id,
            "world_name": result["metadatas"][i].get("world_name", "Unknown World")
            if result["metadatas"] and result["metadatas"][i]
            else "Unknown World",
            "world_description": result["documents"][i]
            if result["documents"] and len(result["documents"]) > i
            else "No description available",
            "genre": result["metadatas"][i].get("genre", "Unknown")
            if result["metadatas"] and result["metadatas"][i]
            else "Unknown",
            "dominant_species": result["metadatas"][i].get(
                "dominant_species", "Unknown"
            )
            if result["metadatas"] and result["metadatas"][i]
            else "Unknown",
            "magic_presence": result["metadatas"][i].get("magic_presence", False)
            if result["metadatas"] and result["metadatas"][i]
            else False,
            "governance": result["metadatas"][i].get("governance", "Unknown")
            if result["metadatas"] and result["metadatas"][i]
            else "Unknown",
        }
        worlds_list.append(world_data)

    # Return at most 3 random worlds
    return random.sample(worlds_list, min(3, len(worlds_list)))


@traceable(run_type="chain", name="Get lore context")
def get_lore_context(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="lores",
    )

    retriever = make_retriever(db_collection, {"world_id": state.get("world_id", "")})

    query = get_multilingual_rag_query(
        state, "lore_search", world_name=state.get("world_name", "Unknown World")
    )
    result = retriever.invoke(query)

    if len(result) > 0:
        state["lore_context"] = "\n".join([doc.page_content for doc in result])
    else:
        state["lore_context"] = "No lore context available yet."

    return state


@traceable(run_type="chain", name="Get character context")
def get_character_context(state: StateSchema) -> StateSchema:
    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name="characters",
    )
    result = db_collection.get(where={"world_id": state.get("world_id", "")})

    if result["ids"]:
        state["character_context"] = "\n".join([doc for doc in result["documents"]])
    else:
        state["character_context"] = "No context provided."

    return state


@traceable(run_type="chain", name="LLM Generate Lore Data")
def llm_generate_lore_data(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = get_i18n_text(state, "generating_lore_data")
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)

    state["active_step"] = "lore_generation"

    prompt_template = get_multilingual_llm_prompt(state, "lore_generation")
    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get("world_name", "World name not provided."),
        world_context=state.get("world_context", "No world context available yet."),
        lore_context=state.get("lore_context", "No lore context available yet."),
        character_context=state.get(
            "character_context", "No character context available yet."
        ),
        world_id=state.get("world_id", str(uuid4())),
    )
    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    llm_dict: dict[str, str] = ast.literal_eval(llm_response)

    state["llm_generated_data"] = [llm_dict]
    state["lore_context"] = llm_dict.get("page_content", "")
    return state


# ------------------------------------------------------------------ #
#                           STORY FUNCTIONS                          #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="LLM Generate World Summary")
def llm_generate_world_summary(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        cue = get_i18n_text(state, "summarizing_story")
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)

    prompt_template = get_multilingual_llm_prompt(state, "world_summary")
    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get("world_name", "World name not provided."),
        world_context=state.get("world_context", "No world context available yet."),
        lore_context=state.get("lore_context", "No lore context available yet."),
        character_context=state.get(
            "character_context", "No character context available yet."
        ),
        world_id=state.get("world_id", str(uuid4())),
    )

    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    if state.get("source") == "cli":
        print("\n")
        play_and_type(llm_response, width=TERMINAL_WIDTH)

    state["world_summary"] = llm_response
    return state


@traceable(run_type="chain", name="LLM Generate Immediate Event Summary")
def llm_generate_immediate_event_summary(state: StateSchema) -> StateSchema:
    prompt_template = get_multilingual_llm_prompt(state, "immediate_event_summary")
    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_name=state.get("world_name", "World name not provided."),
        event_context=state.get("event_context", "No event context available yet."),
        player_answer=state.get("player_answer", "No player answer available yet."),
    )

    truncated_prompt = truncate_structured_prompt(formatted_prompt)

    llm_model = ChatOpenAI(
        model=LLM_NAME,
        temperature=MAIN_TEMP,
        streaming=False,
        max_retries=2,
    )

    raw_output = llm_model.invoke(truncated_prompt).content
    llm_response = (
        raw_output.strip() if isinstance(raw_output, str) else str(raw_output)
    )

    if state.get("source") == "cli":
        print("\n")
        play_and_type(llm_response, width=TERMINAL_WIDTH)

    # Save in collection
    character_id = state.get("character_id")
    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )

    doc = Document(
        page_content=llm_response,
        metadata={
            "source": "AI",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    collection.add_documents([doc])
    state["immediate_events"] = llm_response

    return state


# ------------------------------------------------------------------ #
#                         GAMEPLAY FUNCTIONS                         #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Retrieve past events for player")
def get_event_context(state: StateSchema) -> StateSchema:
    character_id = state.get("character_id")

    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )

    # Récupération directe avec .get()
    result = collection.get()
    
    if not result["ids"]:
        state["event_context"] = ""
        return state

    # Création des documents à partir du résultat
    docs = []
    for i, doc_id in enumerate(result["ids"]):
        doc_content = result["documents"][i] if i < len(result["documents"]) else ""
        doc_metadata = result["metadatas"][i] if i < len(result["metadatas"]) else {}
        
        # Création d'un objet similaire à Document pour maintenir la compatibilité
        doc = type('Doc', (), {
            'page_content': doc_content,
            'metadata': doc_metadata
        })()
        docs.append(doc)

    # Tri par récence
    docs_sorted = sorted(
        docs, key=lambda d: d.metadata.get("timestamp", ""), reverse=False
    )

    # Limite pour éviter d'inonder le contexte
    max_events = 20
    final_docs = docs_sorted[:max_events]

    # Formatage identique à avant
    lines = []
    for d in final_docs:
        text = (d.page_content or "").strip()
        src = str(d.metadata.get("source", "")).lower()
        if src == "ai":
            text = f"\nAI / IA: {text}\n"
        else:
            text = f"\nPlayer / Joueur: {text}\n"
        lines.append(text)

    state["event_context"] = "\n".join(lines)
    return state


@traceable(run_type="chain", name="LLM generate next narrative cue")
def llm_generate_next_prompt(state: StateSchema) -> StateSchema:
    prompt_template = get_multilingual_llm_prompt(state, "next_prompt")
    prompt = PromptTemplate.from_template(prompt_template, template_format="jinja2")
    formatted_prompt = prompt.format(
        world_context=state.get("world_context", ""),
        event_context=state.get("event_context", ""),
        lore_context=state.get("lore_context", ""),
        character_context=state.get("character_context", ""),
        character_name=state.get("character_name", ""),
    )

    llm_model = ChatOpenAI(model=LLM_NAME_THINKING, temperature=MAIN_TEMP)
    result = llm_model.invoke(truncate_structured_prompt(formatted_prompt)).content
    result = result.strip() if isinstance(result, str) else str(result)

    # Save in collection
    character_id = state.get("character_id")
    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )

    doc = Document(
        page_content=result,
        metadata={
            "source": "AI",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    collection.add_documents([doc])
    state["ai_question"] = result

    if state.get("source") == "cli":
        print("\n")
        play_and_type(result, width=TERMINAL_WIDTH)

    return state


@traceable(run_type="chain", name="Record player response")
def record_player_response(state: StateSchema) -> StateSchema:
    if state.get("source") == "cli":
        time.sleep(7.5)
        state["player_answer"] = get_player_answer("What do you want to do? ")
    character_id = state.get("character_id")
    collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=f"{character_id}_events",
    )
    doc = Document(
        page_content=state.get("player_answer", ""),
        metadata={
            "source": "player",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    collection.add_documents([doc])
    return state


@traceable(run_type="chain", name="Ask if player wants to continue")
def ask_to_continue_or_stop(state: StateSchema) -> StateSchema:
    time.sleep(7.5)
    cue = get_i18n_text(state, "ask_continue")
    answer = get_player_answer(cue, force_type=True).strip().lower()
    state["continue_story"] = answer in ["yes", "y", "oui", "o"]
    return state


# ------------------------------------------------------------------ #
#                          UTILITY FUNCTIONS                         #
# ------------------------------------------------------------------ #


@traceable(run_type="chain", name="Save list of documents to ChromaDB")
def save_documents_to_chroma(state: StateSchema) -> StateSchema:
    world_id = state.get("world_id", "")
    llm_generated_data = state.get("llm_generated_data", [])

    # Convert to LangChain Document format
    documents_to_save = [
        Document(
            page_content=document.get("page_content", ""),
            metadata=document.get("metadata", {}),
        )
        for document in llm_generated_data
    ]

    if state.get("active_step") == "world_creation":
        ids = [world_id]
        collection_name = "worlds"
    elif state.get("active_step") == "lore_generation":
        ids = [str(uuid4()) for _ in documents_to_save]
        collection_name = "lores"
    elif state.get("active_step") == "character_creation":
        ids = [str(uuid4()) for _ in documents_to_save]
        collection_name = "characters"
    else:
        ids = [str(uuid4()) for _ in documents_to_save]
        collection_name = "test"

    db_collection = Chroma(
        client=CHROMA_DB_CLIENT,
        embedding_function=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        collection_name=collection_name,
    )

    db_collection.add_documents(documents_to_save, ids=ids)
    return state


# ------------------------------------------------------------------ #
#                   CONDITIONAL VALIDATOR FUNCTIONS                  #
# ------------------------------------------------------------------ #


def check_input_validity(
    state: StateSchema,
) -> Literal["__valid__", "__invalid__"]:
    res = "__valid__"

    if not state.get("user_input"):
        cue = get_i18n_text(state, "input_missing")
        print("\n")
        play_and_type(cue, width=TERMINAL_WIDTH)
        res = "__invalid__"

    state["user_input"] = ""
    return res


# ------------------------------------------------------------------ #
#                               ROUTERS                              #
# ------------------------------------------------------------------ #


def route_world_creation(
    state: StateSchema,
) -> Literal["__exists__", "__must_configure__", "__must_restart_init__"]:
    if state.get("must_restart_init"):
        return "__must_restart_init__"
    elif state.get("create_new_world"):
        return "__must_configure__"
    else:
        return "__exists__"


def route_character_creation(
    state: StateSchema,
) -> Literal["__exists__", "__must_configure__", "__must_restart_character__"]:
    if state.get("must_restart_character"):
        return "__must_restart_character__"
    elif state.get("create_new_character"):
        return "__must_configure__"
    else:
        return "__exists__"


def route_after_saving(
    state: StateSchema,
) -> Literal["__from_world__", "__from_lore__", "__from_character__"]:
    if state.get("active_step") == "world_creation":
        return "__from_world__"
    elif state.get("active_step") == "character_creation":
        return "__from_character__"
    else:
        return "__from_lore__"


# ------------------------------------------------------------------ #
#                                GRAPH                               #
# ------------------------------------------------------------------ #

graph = StateGraph(StateSchema)

# ------------------------------ Nodes ----------------------------- #

# World Generation Nodes
graph.add_node("ask_if_new_world", ask_if_new_world)
graph.add_node("ask_world_name", ask_world_name)
graph.add_node("check_world_exists", check_world_exists)
graph.add_node("ask_world_genre", ask_world_genre)
graph.add_node("ask_story_directives", ask_story_directives)
graph.add_node("llm_generate_world_data", llm_generate_world_data)

# Character Creation Nodes
graph.add_node("ask_create_new_character", ask_create_new_character)
graph.add_node("ask_new_character_name", ask_new_character_name)
graph.add_node("check_character_exists", check_character_exists)
graph.add_node("ask_character_details", ask_character_details)
graph.add_node("llm_generate_character_data", llm_generate_character_data)

# Lore Generation Nodes
graph.add_node("get_world_context", get_world_context)
graph.add_node("get_lore_context", get_lore_context)
graph.add_node("get_character_context", get_character_context)
graph.add_node("llm_generate_lore_data", llm_generate_lore_data)

# World Summary Nodes
graph.add_node("llm_generate_world_summary", llm_generate_world_summary)

# Gameplay Nodes
graph.add_node("get_event_context", get_event_context)
graph.add_node("llm_generate_next_prompt", llm_generate_next_prompt)
graph.add_node("record_player_response", record_player_response)
graph.add_node("ask_to_continue_or_stop", ask_to_continue_or_stop)

# Validators
graph.add_node("check_input_validity", check_input_validity)

# Routing Nodes
graph.add_node("route_character_creation", route_character_creation)
graph.add_node("route_world_creation", route_world_creation)
graph.add_node("route_after_saving", route_after_saving)

# Utility Functions
graph.add_node("save_documents_to_chroma", save_documents_to_chroma)

# ---------------------------- Workflow ---------------------------- #

# Entry point
graph.set_entry_point("ask_if_new_world")

# Ask if player wants to create a new world block
graph.add_edge("ask_if_new_world", "ask_world_name")
graph.add_conditional_edges(
    "ask_world_name",
    check_input_validity,
    {
        "__valid__": "check_world_exists",
        "__invalid__": "ask_world_name",
    },
)
graph.add_conditional_edges(
    "check_world_exists",
    route_world_creation,
    {
        "__must_restart_init__": "ask_if_new_world",
        "__must_configure__": "ask_world_genre",
        "__exists__": "ask_create_new_character",
    },
)

# World creation block
graph.add_edge("ask_world_genre", "ask_story_directives")
graph.add_edge("ask_story_directives", "llm_generate_world_data")
graph.add_edge("llm_generate_world_data", "save_documents_to_chroma")

# Character creation block
graph.add_edge("ask_create_new_character", "ask_new_character_name")
graph.add_conditional_edges(
    "ask_new_character_name",
    check_input_validity,
    {
        "__valid__": "check_character_exists",
        "__invalid__": "ask_new_character_name",
    },
)
graph.add_conditional_edges(
    "check_character_exists",
    route_character_creation,
    {
        "__must_restart_character__": "ask_create_new_character",
        "__must_configure__": "ask_character_details",
        "__exists__": "get_world_context",
    },
)
graph.add_edge("ask_character_details", "llm_generate_character_data")
graph.add_edge("llm_generate_character_data", "save_documents_to_chroma")

# Lore creation block
graph.add_edge("get_world_context", "get_lore_context")
graph.add_edge("get_lore_context", "get_character_context")
graph.add_edge("get_character_context", "llm_generate_lore_data")
graph.add_edge("llm_generate_lore_data", "save_documents_to_chroma")

# Routing after saving documents block
graph.add_conditional_edges(
    "save_documents_to_chroma",
    route_after_saving,
    {
        "__from_world__": "ask_new_character_name",
        "__from_character__": "get_world_context",
        "__from_lore__": "llm_generate_world_summary",
    },
)

graph.add_edge("llm_generate_world_summary", "ask_to_continue_or_stop")

# World summary generation block
graph.add_edge("get_event_context", "llm_generate_next_prompt")
graph.add_edge("llm_generate_next_prompt", "record_player_response")
graph.add_edge("record_player_response", "ask_to_continue_or_stop")

graph.add_conditional_edges(
    "ask_to_continue_or_stop",
    lambda state: "__continue__" if state.get("continue_story") else "__end__",
    {
        "__continue__": "get_event_context",
        "__end__": END,
    },
)

# Final state
main_graph = graph.compile()
