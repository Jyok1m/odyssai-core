"""
MongoDB client wrapper for OdyssAI Core
Provides high-level database operations with schema validation
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from .connection import get_database
from .schemas import VALIDATORS

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    High-level MongoDB client wrapper for common operations with schema validation
    """
    
    def __init__(self, database_name: str = "odyssai", validate_schemas: bool = True):
        """
        Initialize MongoDB client
        
        Args:
            database_name (str): Name of the database
            validate_schemas (bool): Whether to validate documents against schemas
        """
        self.database_name = database_name
        self.validate_schemas = validate_schemas
        self._db: Optional[Database] = None
    
    @property
    def db(self) -> Database:
        """Get database instance"""
        if self._db is None:
            self._db = get_database(self.database_name)
        return self._db
    
    def get_collection(self, collection_name: str) -> Collection:
        """
        Get collection instance
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Collection: The MongoDB collection instance
        """
        return self.db[collection_name]
    
    def _validate_document(self, collection_name: str, document: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate document against schema if validation is enabled
        
        Args:
            collection_name (str): Name of the collection
            document (Dict): Document to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        if not self.validate_schemas or collection_name not in VALIDATORS:
            return True, []
        
        validator = VALIDATORS[collection_name]
        return validator(document)
    
    def insert_one(self, collection_name: str, document: Dict[str, Any], 
                   skip_validation: bool = False) -> Optional[str]:
        """
        Insert a single document with schema validation
        
        Args:
            collection_name (str): Name of the collection
            document (Dict): Document to insert
            skip_validation (bool): Skip schema validation for this insert
            
        Returns:
            Optional[str]: The inserted document's ID as string, None if failed
        """
        try:
            # Validate document if enabled
            if not skip_validation:
                is_valid, errors = self._validate_document(collection_name, document)
                if not is_valid:
                    logger.error(f"Document validation failed for {collection_name}: {errors}")
                    return None
            
            collection = self.get_collection(collection_name)
            result = collection.insert_one(document)
            logger.info(f"Document inserted in {collection_name} with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error inserting document in {collection_name}: {e}")
            return None
    
    def insert_many(self, collection_name: str, documents: List[Dict[str, Any]], 
                    skip_validation: bool = False) -> List[str]:
        """
        Insert multiple documents with schema validation
        
        Args:
            collection_name (str): Name of the collection
            documents (List[Dict]): List of documents to insert
            skip_validation (bool): Skip schema validation for this insert
            
        Returns:
            List[str]: List of inserted document IDs as strings
        """
        try:
            # Validate all documents if enabled
            if not skip_validation:
                for i, document in enumerate(documents):
                    is_valid, errors = self._validate_document(collection_name, document)
                    if not is_valid:
                        logger.error(f"Document {i} validation failed for {collection_name}: {errors}")
                        return []
            
            collection = self.get_collection(collection_name)
            result = collection.insert_many(documents)
            logger.info(f"{len(result.inserted_ids)} documents inserted in {collection_name}")
            return [str(id_) for id_ in result.inserted_ids]
        except PyMongoError as e:
            logger.error(f"Error inserting documents in {collection_name}: {e}")
            return []
    
    def find_one(self, collection_name: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single document
        
        Args:
            collection_name (str): Name of the collection
            filter_dict (Dict): Query filter
            
        Returns:
            Optional[Dict]: The found document, None if not found
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.find_one(filter_dict)
            if result:
                # Convert ObjectId to string for JSON serialization
                result["_id"] = str(result["_id"])
            return result
        except PyMongoError as e:
            logger.error(f"Error finding document in {collection_name}: {e}")
            return None
    
    def find_many(self, collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, 
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find multiple documents
        
        Args:
            collection_name (str): Name of the collection
            filter_dict (Dict): Query filter (default: {})
            limit (int): Maximum number of documents to return
            
        Returns:
            List[Dict]: List of found documents
        """
        try:
            collection = self.get_collection(collection_name)
            filter_dict = filter_dict or {}
            
            cursor = collection.find(filter_dict)
            if limit:
                cursor = cursor.limit(limit)
            
            results = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            
            logger.info(f"Found {len(results)} documents in {collection_name}")
            return results
        except PyMongoError as e:
            logger.error(f"Error finding documents in {collection_name}: {e}")
            return []
    
    def update_one(self, collection_name: str, filter_dict: Dict[str, Any], 
                   update_dict: Dict[str, Any]) -> bool:
        """
        Update a single document
        
        Args:
            collection_name (str): Name of the collection
            filter_dict (Dict): Query filter
            update_dict (Dict): Update operations
            
        Returns:
            bool: True if document was updated, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.update_one(filter_dict, {"$set": update_dict})
            success = result.modified_count > 0
            if success:
                logger.info(f"Document updated in {collection_name}")
            return success
        except PyMongoError as e:
            logger.error(f"Error updating document in {collection_name}: {e}")
            return False
    
    def delete_one(self, collection_name: str, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete a single document
        
        Args:
            collection_name (str): Name of the collection
            filter_dict (Dict): Query filter
            
        Returns:
            bool: True if document was deleted, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.delete_one(filter_dict)
            success = result.deleted_count > 0
            if success:
                logger.info(f"Document deleted from {collection_name}")
            return success
        except PyMongoError as e:
            logger.error(f"Error deleting document from {collection_name}: {e}")
            return False
    
    def count_documents(self, collection_name: str, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents in collection
        
        Args:
            collection_name (str): Name of the collection
            filter_dict (Dict): Query filter (default: {})
            
        Returns:
            int: Number of documents matching the filter
        """
        try:
            collection = self.get_collection(collection_name)
            filter_dict = filter_dict or {}
            count = collection.count_documents(filter_dict)
            logger.info(f"Found {count} documents in {collection_name}")
            return count
        except PyMongoError as e:
            logger.error(f"Error counting documents in {collection_name}: {e}")
            return 0
    
    def find_by_id(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a document by its ObjectId
        
        Args:
            collection_name (str): Name of the collection
            document_id (str): The document ID as string
            
        Returns:
            Optional[Dict]: The found document, None if not found
        """
        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(document_id)
            return self.find_one(collection_name, {"_id": object_id})
        except Exception as e:
            logger.error(f"Error finding document by ID {document_id}: {e}")
            return None
    
    def update_by_id(self, collection_name: str, document_id: str, update_dict: Dict[str, Any]) -> bool:
        """
        Update a document by its ObjectId
        
        Args:
            collection_name (str): Name of the collection
            document_id (str): The document ID as string
            update_dict (Dict): Update operations
            
        Returns:
            bool: True if document was updated, False otherwise
        """
        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(document_id)
            return self.update_one(collection_name, {"_id": object_id}, update_dict)
        except Exception as e:
            logger.error(f"Error updating document by ID {document_id}: {e}")
            return False
    
    def delete_by_id(self, collection_name: str, document_id: str) -> bool:
        """
        Delete a document by its ObjectId
        
        Args:
            collection_name (str): Name of the collection
            document_id (str): The document ID as string
            
        Returns:
            bool: True if document was deleted, False otherwise
        """
        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(document_id)
            return self.delete_one(collection_name, {"_id": object_id})
        except Exception as e:
            logger.error(f"Error deleting document by ID {document_id}: {e}")
            return False
    
    @staticmethod
    def is_valid_object_id(document_id: str) -> bool:
        """
        Check if a string is a valid ObjectId
        
        Args:
            document_id (str): The ID string to validate
            
        Returns:
            bool: True if valid ObjectId format, False otherwise
        """
        try:
            ObjectId(document_id)
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_object_id() -> str:
        """
        Generate a new ObjectId as string
        
        Returns:
            str: New ObjectId as string
        """
        return str(ObjectId())
    
    def validate_document_schema(self, collection_name: str, document: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Manually validate a document against its schema
        
        Args:
            collection_name (str): Name of the collection
            document (Dict): Document to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        return self._validate_document(collection_name, document)
    
    def get_collection_schema_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get schema information for a collection
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Dict: Schema information
        """
        if collection_name not in VALIDATORS:
            return {"has_schema": False, "message": f"No schema defined for {collection_name}"}
        
        return {
            "has_schema": True,
            "collection_name": collection_name,
            "validator_available": True,
            "validation_enabled": self.validate_schemas
        }
