"""
Database schemas for OdyssAI Core
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class UserRole(Enum):
    """User roles enumeration"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

@dataclass
class UserSchema:
    """User document schema"""
    # Player info
    uuid: str
    username: str
    password: str

    created_at: datetime

    # Game info
    current_world_id: Optional[str] = None
    current_world_name: Optional[str] = None
    current_character_id: Optional[str] = None
    current_character_name: Optional[str] = None

    # User preferences
    language: str = "en"  # Default to English ('en' or 'fr')

    # Extra data
    last_login: Optional[datetime] = None
    role: UserRole = UserRole.USER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion"""
        data = asdict(self)
        # Convert enum to string
        data['role'] = self.role.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSchema':
        """Create UserSchema from dictionary"""
        # Convert string back to enum
        if 'role' in data:
            data['role'] = UserRole(data['role'])
        return cls(**data)
    
    def validate(self) -> List[str]:
        """Validate user data and return list of errors"""
        errors = []
        
        if not self.username or len(self.username) < 3:
            errors.append("Username must be at least 3 characters long")
        
        return errors

@dataclass
class InteractionSchema:
    """AI interaction document schema"""
    user_uuid: str  # ObjectId as string
    message: Dict[Any, Any]
    world_id: Optional[str] = None
    character_id: Optional[str] = None
    interaction_source: str = "ai"  # ai or user
    timestamp: datetime = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractionSchema':
        """Create InteractionSchema from dictionary"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """Validate AI interaction data and return list of errors"""
        errors = []
        
        if not self.user_uuid:
            errors.append("user_id is required")
        
        if not self.interaction_source:
            errors.append("interaction_source is required")
        
        return errors


# Schema validation utilities
class SchemaValidator:
    """Utility class for schema validation"""
    
    @staticmethod
    def validate_user(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate user data against UserSchema"""
        try:
            errors = []
            
            # Check required fields
            if not data.get('username') or len(data.get('username', '')) < 3:
                errors.append("Username must be at least 3 characters long")
            
            if not data.get('uuid'):
                errors.append("UUID is required")
                
            if not data.get('password'):
                errors.append("Password is required")
                
            if not data.get('created_at'):
                errors.append("Created_at is required")
            
            # Validate role if present
            if 'role' in data and data['role'] not in ['user', 'admin', 'moderator']:
                errors.append("Role must be one of: user, admin, moderator")
            
            return len(errors) == 0, errors
        except Exception as e:
            return False, [f"Schema validation error: {str(e)}"]
    
    @staticmethod
    def validate_ai_interaction(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate AI interaction data against InteractionSchema"""
        try:
            interaction = InteractionSchema.from_dict(data)
            errors = interaction.validate()
            return len(errors) == 0, errors
        except Exception as e:
            return False, [f"Schema validation error: {str(e)}"]


# Schema registry for easy access
SCHEMAS = {
    "users": UserSchema,
    "ai_interactions": InteractionSchema,
}

VALIDATORS = {
    "users": SchemaValidator.validate_user,
    "ai_interactions": SchemaValidator.validate_ai_interaction,
}