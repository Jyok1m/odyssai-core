"""
Internationalization utilities for API error messages and responses
"""
from typing import Dict, Any, Optional


def get_error_message(language: str, error_key: str, **kwargs) -> str:
    """
    Get localized error message based on language and error key
    
    Args:
        language: Language code ('fr' or 'en')
        error_key: Key identifying the specific error message
        **kwargs: Variables to interpolate into the message
    
    Returns:
        Localized error message string
    """
    if language not in ['fr', 'en']:
        language = 'en'
    
    # Error message translations
    error_messages = {
        # Validation errors
        "missing_fields": {
            "en": "Missing required fields",
            "fr": "Champs obligatoires manquants"
        },
        "invalid_language": {
            "en": "Language must be either 'fr' or 'en'",
            "fr": "La langue doit être 'fr' ou 'en'"
        },
        
        # User-related errors
        "user_already_exists": {
            "en": "User already exists",
            "fr": "L'utilisateur existe déjà"
        },
        "user_not_found": {
            "en": "User not found",
            "fr": "Utilisateur non trouvé"
        },
        "invalid_credentials": {
            "en": "Invalid username or password",
            "fr": "Nom d'utilisateur ou mot de passe incorrect"
        },
        "failed_create_user": {
            "en": "Failed to create user",
            "fr": "Échec de la création de l'utilisateur"
        },
        "failed_update_user": {
            "en": "Failed to update user game context",
            "fr": "Échec de la mise à jour du contexte de jeu de l'utilisateur"
        },
        "failed_update_language": {
            "en": "Failed to update user language",
            "fr": "Échec de la mise à jour de la langue de l'utilisateur"
        },
        "failed_clear_context": {
            "en": "Failed to clear user game context",
            "fr": "Échec de l'effacement du contexte de jeu de l'utilisateur"
        },
        "missing_game_context": {
            "en": "At least one game context field must be provided",
            "fr": "Au moins un champ de contexte de jeu doit être fourni"
        },
        
        # Interaction errors
        "invalid_interaction_source": {
            "en": "interaction_source must be either 'user' or 'ai'",
            "fr": "interaction_source doit être 'user' ou 'ai'"
        },
        "failed_save_interaction": {
            "en": "Failed to save interaction",
            "fr": "Échec de l'enregistrement de l'interaction"
        },
        "failed_retrieve_interactions": {
            "en": "Failed to retrieve interactions: {error}",
            "fr": "Échec de la récupération des interactions : {error}"
        },
        "failed_delete_interactions": {
            "en": "Failed to delete interactions: {error}",
            "fr": "Échec de la suppression des interactions : {error}"
        },
        "user_uuid_required": {
            "en": "user_uuid parameter is required",
            "fr": "Le paramètre user_uuid est obligatoire"
        },
        
        # World-related errors
        "world_name_or_id_required": {
            "en": "Either world_name or world_id parameter is required",
            "fr": "Le paramètre world_name ou world_id est obligatoire"
        },
        "world_id_required": {
            "en": "world_id parameter is required",
            "fr": "Le paramètre world_id est obligatoire"
        },
        
        # Character-related errors
        "character_name_or_id_required": {
            "en": "Either character_name or character_id parameter is required",
            "fr": "Le paramètre character_name ou character_id est obligatoire"
        },
        "character_id_required": {
            "en": "character_id parameter is required",
            "fr": "Le paramètre character_id est obligatoire"
        },
        
        # Generic errors
        "internal_error": {
            "en": "Internal server error",
            "fr": "Erreur interne du serveur"
        },
        "validation_failed": {
            "en": "Validation failed",
            "fr": "Échec de la validation"
        }
    }
    
    # Get the message template
    message_template = error_messages.get(error_key, {}).get(language)
    if not message_template:
        # Fallback to English if key not found
        message_template = error_messages.get(error_key, {}).get('en', f'Unknown error: {error_key}')
    
    # Interpolate variables if provided
    if kwargs:
        try:
            return message_template.format(**kwargs)
        except KeyError:
            # If interpolation fails, return the template as-is
            return message_template
    
    return message_template


def get_success_message(language: str, message_key: str, **kwargs) -> str:
    """
    Get localized success message based on language and message key
    
    Args:
        language: Language code ('fr' or 'en')
        message_key: Key identifying the specific success message
        **kwargs: Variables to interpolate into the message
    
    Returns:
        Localized success message string
    """
    if language not in ['fr', 'en']:
        language = 'en'
    
    # Success message translations
    success_messages = {
        # User-related success messages
        "user_created": {
            "en": "User created successfully",
            "fr": "Utilisateur créé avec succès"
        },
        "login_successful": {
            "en": "Login successful",
            "fr": "Connexion réussie"
        },
        "user_context_updated": {
            "en": "User game context updated successfully",
            "fr": "Contexte de jeu de l'utilisateur mis à jour avec succès"
        },
        "language_updated": {
            "en": "User language updated successfully",
            "fr": "Langue de l'utilisateur mise à jour avec succès"
        },
        "context_cleared": {
            "en": "User game context cleared successfully",
            "fr": "Contexte de jeu de l'utilisateur effacé avec succès"
        },
        "interaction_saved": {
            "en": "Interaction saved successfully",
            "fr": "Interaction enregistrée avec succès"
        },
        "interactions_found": {
            "en": "Found {count} interactions",
            "fr": "{count} interactions trouvées"
        },
        "interactions_deleted": {
            "en": "Successfully deleted {count} interactions for user {user_uuid}",
            "fr": "{count} interactions supprimées avec succès pour l'utilisateur {user_uuid}"
        },
        
        # World-related success messages
        "world_created": {
            "en": "World created successfully",
            "fr": "Monde créé avec succès"
        },
        "world_synopsis_generated": {
            "en": "World synopsis generated successfully",
            "fr": "Synopsis du monde généré avec succès"
        },
        "world_found": {
            "en": "World found",
            "fr": "Monde trouvé"
        },
        "world_not_found": {
            "en": "World not found",
            "fr": "Monde non trouvé"
        },
        
        # Character-related success messages
        "character_created": {
            "en": "Character created successfully",
            "fr": "Personnage créé avec succès"
        },
        "character_found": {
            "en": "Character found",
            "fr": "Personnage trouvé"
        },
        "character_not_found": {
            "en": "Character not found",
            "fr": "Personnage non trouvé"
        },
        
        # Gameplay success messages
        "game_joined": {
            "en": "Game joined successfully",
            "fr": "Jeu rejoint avec succès"
        },
        "prompt_generated": {
            "en": "Game prompt generated successfully",
            "fr": "Invite de jeu générée avec succès"
        },
        "action_registered": {
            "en": "Player action registered successfully",
            "fr": "Action du joueur enregistrée avec succès"
        }
    }
    
    # Get the message template
    message_template = success_messages.get(message_key, {}).get(language)
    if not message_template:
        # Fallback to English if key not found
        message_template = success_messages.get(message_key, {}).get('en', f'Unknown message: {message_key}')
    
    # Interpolate variables if provided
    if kwargs:
        try:
            return message_template.format(**kwargs)
        except KeyError:
            # If interpolation fails, return the template as-is
            return message_template
    
    return message_template


def get_language_from_request(request) -> str:
    """
    Extract language preference from Flask request
    
    Args:
        request: Flask request object
        
    Returns:
        Language code ('fr' or 'en'), defaults to 'en'
    """
    # Try to get language from query parameters first
    lang = request.args.get('lang')
    
    # If not in query, try to get from JSON body
    if not lang and request.is_json:
        data = request.get_json()
        if data and isinstance(data, dict):
            lang = data.get('language')
    
    # Validate and return
    if lang not in ['fr', 'en']:
        return 'en'
    
    return lang


def create_error_response(language: str, error_key: str, status_code: int = 400, **kwargs) -> tuple[Dict[str, Any], int]:
    """
    Create a standardized error response with localized message
    
    Args:
        language: Language code ('fr' or 'en')
        error_key: Key identifying the specific error message
        status_code: HTTP status code for the response
        **kwargs: Variables to interpolate into the message
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    error_message = get_error_message(language, error_key, **kwargs)
    
    response = {
        "success": False,
        "error": error_message,
        "error_key": error_key,
        "language": language
    }
    
    return response, status_code


def create_success_response(language: str, message_key: str, data: Optional[Dict[str, Any]] = None, status_code: int = 200, **kwargs) -> tuple[Dict[str, Any], int]:
    """
    Create a standardized success response with localized message
    
    Args:
        language: Language code ('fr' or 'en')
        message_key: Key identifying the specific success message
        data: Additional data to include in the response
        status_code: HTTP status code for the response
        **kwargs: Variables to interpolate into the message
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    success_message = get_success_message(language, message_key, **kwargs)
    
    response = {
        "success": True,
        "message": success_message,
        "language": language
    }
    
    # Add additional data if provided
    if data:
        response.update(data)
    
    return response, status_code
