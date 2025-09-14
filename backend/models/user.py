"""User model and database operations."""

from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
from passlib.context import CryptContext
from jose import JWTError, jwt
from config import settings
from database.mongodb import get_database
from models.schemas import User, UserCreate, UserLogin, Token, TokenData, ChatSession, ChatSessionCreate
from loguru import logger
import secrets


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserModel:
    """User model and database operations."""
    
    def __init__(self):
        self.collection_name = "users"
    
    async def get_collection(self):
        """Get users collection."""
        db = await get_database()
        return db[self.collection_name]
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify JWT token and return token data."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return TokenData(user_id=user_id)
        except JWTError:
            return None
    
    async def create_user(self, user: UserCreate) -> User:
        """Create a new user."""
        collection = await self.get_collection()
        
        # Check if user already exists
        existing_user = await collection.find_one({
            "$or": [
                {"email": user.email},
                {"username": user.username}
            ]
        })
        
        if existing_user:
            if existing_user["email"] == user.email:
                raise ValueError("Email already registered")
            else:
                raise ValueError("Username already taken")
        
        # Create user document
        user_doc = {
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "hashed_password": self.hash_password(user.password),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = await collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        
        return User(
            id=str(result.inserted_id),
            email=user_doc["email"],
            username=user_doc["username"],
            full_name=user_doc["full_name"],
            is_active=user_doc["is_active"],
            created_at=user_doc["created_at"],
            last_login=user_doc["last_login"]
        )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        collection = await self.get_collection()
        user_doc = await collection.find_one({"email": email})
        
        if not user_doc:
            return None
        
        if not self.verify_password(password, user_doc["hashed_password"]):
            return None
        
        # Update last login
        await collection.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        return User(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            username=user_doc["username"],
            full_name=user_doc["full_name"],
            is_active=user_doc["is_active"],
            created_at=user_doc["created_at"],
            last_login=datetime.utcnow()
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        collection = await self.get_collection()
        user_doc = await collection.find_one({"_id": ObjectId(user_id)})
        
        if not user_doc:
            return None
        
        return User(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            username=user_doc["username"],
            full_name=user_doc["full_name"],
            is_active=user_doc["is_active"],
            created_at=user_doc["created_at"],
            last_login=user_doc["last_login"]
        )
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        collection = await self.get_collection()
        user_doc = await collection.find_one({"email": email})
        
        if not user_doc:
            return None
        
        return User(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            username=user_doc["username"],
            full_name=user_doc["full_name"],
            is_active=user_doc["is_active"],
            created_at=user_doc["created_at"],
            last_login=user_doc["last_login"]
        )


class ChatSessionModel:
    """Chat session model and database operations."""
    
    def __init__(self):
        self.collection_name = "chat_sessions"
    
    async def get_collection(self):
        """Get chat sessions collection."""
        db = await get_database()
        return db[self.collection_name]
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(32)
    
    async def create_session(self, user_id: str, title: str) -> ChatSession:
        """Create a new chat session."""
        collection = await self.get_collection()
        
        session_doc = {
            "session_id": self.generate_session_id(),
            "user_id": user_id,
            "title": title,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "message_count": 0,
            "is_active": True
        }
        
        result = await collection.insert_one(session_doc)
        
        return ChatSession(
            id=str(result.inserted_id),
            user_id=session_doc["user_id"],
            title=session_doc["title"],
            created_at=session_doc["created_at"],
            last_activity=session_doc["last_activity"],
            message_count=session_doc["message_count"],
            is_active=session_doc["is_active"]
        )
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[ChatSession]:
        """Get all sessions for a user."""
        collection = await self.get_collection()
        
        cursor = collection.find(
            {"user_id": user_id, "is_active": True}
        ).sort("last_activity", -1).limit(limit)
        
        sessions = []
        async for doc in cursor:
            sessions.append(ChatSession(
                id=str(doc["_id"]),
                user_id=doc["user_id"],
                title=doc["title"],
                created_at=doc["created_at"],
                last_activity=doc["last_activity"],
                message_count=doc["message_count"],
                is_active=doc["is_active"]
            ))
        
        return sessions
    
    async def get_session_by_id(self, session_id: str, user_id: str) -> Optional[ChatSession]:
        """Get a specific session by ID."""
        collection = await self.get_collection()
        doc = await collection.find_one({
            "session_id": session_id,
            "user_id": user_id
        })
        
        if not doc:
            return None
        
        return ChatSession(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            title=doc["title"],
            created_at=doc["created_at"],
            last_activity=doc["last_activity"],
            message_count=doc["message_count"],
            is_active=doc["is_active"]
        )
    
    async def update_session_activity(self, session_id: str, user_id: str):
        """Update session last activity and increment message count."""
        collection = await self.get_collection()
        await collection.update_one(
            {"session_id": session_id, "user_id": user_id},
            {
                "$set": {"last_activity": datetime.utcnow()},
                "$inc": {"message_count": 1}
            }
        )
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session (soft delete by setting is_active to False)."""
        collection = await self.get_collection()
        result = await collection.update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0


# Global instances
user_model = UserModel()
chat_session_model = ChatSessionModel()


