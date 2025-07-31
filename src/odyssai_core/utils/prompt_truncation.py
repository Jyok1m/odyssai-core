import re
import tiktoken

# Modèle utilisé
LLM_NAME = "gpt-4o"

# Limites de tokens pour un coût < $0.10
MAX_TOTAL_TOKENS = 20_000
RESERVED_FOR_OUTPUT = 5_000
MAX_INPUT_TOKENS = MAX_TOTAL_TOKENS - RESERVED_FOR_OUTPUT

# Nombre minimal de tokens à conserver par bloc
MIN_TOKENS_PER_SECTION = 100


def truncate_flat_text(text: str, max_tokens: int, enc) -> str:
    return enc.decode(enc.encode(text)[:max_tokens])


def truncate_structured_prompt(prompt: str, model: str = LLM_NAME) -> str:
    """
    Troncature d’un prompt structuré en blocs ## Title sans dépasser la limite GPT-4o.
    Chaque bloc garde au moins MIN_TOKENS_PER_SECTION tokens si possible.
    """

    enc = tiktoken.encoding_for_model(model)

    # Découpe en sections de type ## Title
    section_pattern = re.compile(r"(## .+?\n)(.*?)(?=\n## |\Z)", re.DOTALL)
    matches = section_pattern.findall(prompt)

    # Si non structuré, fallback global
    if not matches:
        return truncate_flat_text(prompt, MAX_INPUT_TOKENS, enc)

    # Encode chaque section et calcule les tokens
    encoded_sections = []
    total_tokens = 0
    for header, body in matches:
        tokens = enc.encode(body)
        encoded_sections.append((header, body, tokens))
        total_tokens += len(tokens)

    # Si déjà dans la limite
    if total_tokens <= MAX_INPUT_TOKENS:
        return prompt

    # Troncature progressive
    overflow = total_tokens - MAX_INPUT_TOKENS
    new_sections = []

    for header, body, tokens in encoded_sections:
        current_len = len(tokens)
        if overflow <= 0:
            new_sections.append((header, body))
            continue

        reducible = max(current_len - MIN_TOKENS_PER_SECTION, 0)
        reduction = min(reducible, overflow)
        reduced_tokens = tokens[: current_len - reduction]
        reduced_body = enc.decode(reduced_tokens)

        new_sections.append((header, reduced_body))
        overflow -= reduction

    # Reconstruction
    return "\n\n".join(header + body for header, body in new_sections)
