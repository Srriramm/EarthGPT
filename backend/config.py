"""Configuration settings for the Sustainability Assistant."""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Claude API Configuration
    claude_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = "claude-3-5-haiku-20241022"
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # Database Configuration (MongoDB only)
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "earthgpt"
    
    # Vector Database Configuration
    chroma_persist_directory: str = "./chroma_db"
    
    # Pinecone Configuration
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/sustainability_assistant.log"
    
    # Memory Configuration
    max_conversation_history: int = 10
    max_context_tokens: int = 8000
    
    # Guardrails Configuration
    enable_guardrails: bool = True
    sustainability_keywords: List[str] = [
        # Core sustainability terms
        "climate", "esg", "renewable", "carbon", "sustainability", "sustainable", "environment", "green",
        "clean energy", "emissions", "footprint", "solar", "wind", "hydro", "biodiversity", 
        "conservation", "circular economy", "circular", "economy", "waste reduction", 
        "energy efficiency", "sustainable development", "climate change", "global warming",
        "recycling", "reuse", "reduce", "waste", "materials", "resources", "lifecycle", 
        "cradle to cradle", "zero waste", "sustainable design",
        
        # Climate agreements and policies
        "paris agreement", "paris accord", "kyoto protocol", "cop", "unfccc", "ipcc",
        "climate summit", "climate conference", "climate accord", "climate treaty",
        "international climate", "global climate", "climate policy", "climate governance",
        "climate framework", "climate convention", "climate negotiation", "climate diplomacy",
        
        # Environmental governance
        "environmental policy", "environmental law", "environmental regulation", 
        "environmental governance", "environmental treaty", "environmental accord",
        "rio declaration", "montreal protocol", "sustainable development goals", "sdgs",
        "agenda 2030", "millennium development goals", "environmental justice",
        
        # Climate science and impacts  
        "greenhouse gas", "greenhouse gases", "ghg", "co2", "methane", "nitrous oxide",
        "global temperature", "sea level rise", "ice melting", "arctic ice", "permafrost",
        "climate tipping point", "climate threshold", "climate sensitivity", "radiative forcing",
        "climate modeling", "climate projection", "climate scenario", "climate impact",
        
        # Energy transition
        "energy transition", "decarbonization", "decarbonisation", "net zero", "carbon neutral",
        "carbon negative", "renewable energy", "clean technology", "green technology",
        "energy storage", "battery technology", "smart grid", "microgrid", "energy security",
        "blockchain", "digital technology", "traceability", "transparency",
        
        # Sustainability frameworks
        "triple bottom line", "people planet profit", "stakeholder capitalism", 
        "impact investing", "green finance", "sustainable finance", "climate finance",
        "carbon pricing", "carbon tax", "cap and trade", "carbon offset", "carbon credit",
        "green bonds", "sustainability bonds", "esg investing", "responsible investment",
        "sustainable investment", "green investment", "climate investment", "esg criteria",
        "esg factors", "esg performance", "esg reporting", "esg disclosure",
        
        # Environmental issues
        "deforestation", "reforestation", "afforestation", "land use", "land use change",
        "ocean acidification", "plastic pollution", "microplastics", "pollution control",
        "air quality", "water quality", "water", "water management", "water conservation", 
        "soil health", "ecosystem services", "natural capital",
        
        # Sustainable practices
        "organic farming", "regenerative agriculture", "permaculture", "sustainable agriculture",
        "green building", "leed", "breeam", "passive house", "green infrastructure",
        "urban planning", "sustainable cities", "smart cities", "public transport",
        "electric vehicle", "ev", "sustainable mobility", "active transport",
        "supply chain", "supply chains", "logistics", "procurement", "sourcing",
        
        # Organizations and bodies
        "unep", "iea", "irena", "world bank", "green climate fund", "gef",
        "wwf", "greenpeace", "environmental ngo", "climate activist", "greta thunberg"
    ]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "protected_namespaces": (),
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
