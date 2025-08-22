import os
import re
import tiktoken
from ..constants.llm_models import LLM_NAME

# ========= Paramètres coût & contexte (surchageables via variables d'env) =========
# Prix par token (texte) – par défaut 4o: $5/M input, $20/M output
PRICE_INPUT_PER_TOKEN = float(os.getenv("LLM_PRICE_INPUT_PER_TOKEN", str(5 / 1_000_000)))
PRICE_OUTPUT_PER_TOKEN = float(os.getenv("LLM_PRICE_OUTPUT_PER_TOKEN", str(20 / 1_000_000)))

# Budget cible par appel
BUDGET_USD = float(os.getenv("LLM_BUDGET_USD", "0.20"))

# Réservation de tokens pour la sortie (plus cher, on réserve)
RESERVED_FOR_OUTPUT = int(os.getenv("LLM_RESERVED_OUTPUT_TOKENS", "3000"))

# Contexte max du modèle (4o ≈ 128k) et marge de sécurité
MODEL_CONTEXT_TOKENS = int(os.getenv("LLM_MODEL_CONTEXT_TOKENS", "128000"))
SAFETY_MARGIN_TOKENS = int(os.getenv("LLM_SAFETY_MARGIN_TOKENS", "500"))

# Nombre minimal de tokens à conserver par bloc ## (surchageable)
MIN_TOKENS_PER_SECTION = int(os.getenv("LLM_MIN_TOKENS_PER_SECTION", "100"))

# ==================== Calcul des plafonds de tokens =====================
# Input max compatible avec le budget : (B - price_out * out_tokens) / price_in
_MAX_INPUT_FROM_BUDGET = max(
    0,
    int((BUDGET_USD - PRICE_OUTPUT_PER_TOKEN * RESERVED_FOR_OUTPUT) / max(PRICE_INPUT_PER_TOKEN, 1e-12))
)

# Plafond total effectif = min(contexte modèle, input + output)
MAX_TOTAL_TOKENS = min(MODEL_CONTEXT_TOKENS - SAFETY_MARGIN_TOKENS, _MAX_INPUT_FROM_BUDGET + RESERVED_FOR_OUTPUT)
MAX_INPUT_TOKENS = max(0, min(_MAX_INPUT_FROM_BUDGET, MAX_TOTAL_TOKENS - RESERVED_FOR_OUTPUT))


# ========================= Encodage & utilitaires =========================
def _get_encoder(model_name: str):
    """
    Récupère l'encodeur tiktoken pour le modèle, avec fallbacks robustes.
    """
    try:
        return tiktoken.encoding_for_model(model_name)
    except Exception:
        try:
            return tiktoken.get_encoding("o200k_base")
        except Exception:
            return tiktoken.get_encoding("cl100k_base")


def truncate_flat_text(text: str, max_tokens: int, enc) -> str:
    """
    Coupe brutalement un texte à max_tokens (sécurisé au niveau des bytes/tokenization).
    """
    if max_tokens <= 0:
        return ""
    return enc.decode(enc.encode(text)[:max_tokens])


# ========================= Troncature structurée =========================
_SECTION_RE = re.compile(r"(## [^\n]+\n)(.*?)(?=\n## |\Z)", re.DOTALL)


def truncate_structured_prompt(prompt: str) -> str:
    """
    Troncature d’un prompt structuré en blocs "## Titre" sans dépasser la limite d'input.
    - Compte les tokens des en-têtes ET des corps de sections.
    - Conserve au moins MIN_TOKENS_PER_SECTION tokens par section si possible.
    - Si l'overflow persiste, fallback à une troncature globale.
    """
    enc = _get_encoder(LLM_NAME)

    matches = list(_SECTION_RE.findall(prompt))

    # Si non structuré, troncature simple
    if not matches:
        return truncate_flat_text(prompt, MAX_INPUT_TOKENS, enc)

    # Encode header + body pour chaque section
    encoded_sections = []
    total_tokens = 0
    for header, body in matches:
        t_header = enc.encode(header)
        t_body = enc.encode(body)
        encoded_sections.append([header, body, t_header, t_body])
        total_tokens += len(t_header) + len(t_body)

    # Si déjà dans la limite d'input
    if total_tokens <= MAX_INPUT_TOKENS:
        return prompt

    # Première passe : réduire les corps au-dessus du minimum
    overflow = total_tokens - MAX_INPUT_TOKENS
    new_sections = []
    for header, body, t_header, t_body in encoded_sections:
        if overflow <= 0:
            new_sections.append((header, body))
            continue

        current_len = len(t_body)
        reducible = max(current_len - MIN_TOKENS_PER_SECTION, 0)
        cut = min(reducible, overflow)

        if cut > 0:
            reduced_tokens = t_body[: current_len - cut]
            body = enc.decode(reduced_tokens)
            overflow -= cut

        new_sections.append((header, body))

    # Si overflow persiste après avoir ramené tous les corps au minimum,
    # fallback à une troncature globale (garantie de respecter MAX_INPUT_TOKENS).
    if overflow > 0:
        joined = "\n\n".join(h + b for (h, b) in new_sections)
        return truncate_flat_text(joined, MAX_INPUT_TOKENS, enc)

    # Reconstruction
    return "\n\n".join(h + b for (h, b) in new_sections)


# ========================= Aides facultatives =========================
def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """
    Estime le coût (USD) pour un appel donné.
    """
    return input_tokens * PRICE_INPUT_PER_TOKEN + output_tokens * PRICE_OUTPUT_PER_TOKEN


def debug_caps() -> dict:
    """
    Renvoie un récap des plafonds calculés (utile pour logs/diagnostics).
    """
    return {
        "budget_usd": BUDGET_USD,
        "reserved_for_output": RESERVED_FOR_OUTPUT,
        "price_in_per_tok": PRICE_INPUT_PER_TOKEN,
        "price_out_per_tok": PRICE_OUTPUT_PER_TOKEN,
        "model_context_tokens": MODEL_CONTEXT_TOKENS,
        "safety_margin_tokens": SAFETY_MARGIN_TOKENS,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_total_tokens": MAX_TOTAL_TOKENS,
        "min_tokens_per_section": MIN_TOKENS_PER_SECTION,
        "llm_name": LLM_NAME,
    }
