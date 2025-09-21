"""Title generation system for chat sessions."""

import re
from typing import Optional
from loguru import logger


class TitleGenerator:
    """Generates meaningful titles from chat messages."""
    
    def __init__(self):
        # Common words to exclude from titles
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'what', 'when', 'where', 'why', 'how',
            'who', 'which', 'whom', 'whose', 'if', 'then', 'else', 'because', 'so', 'as', 'than', 'like',
            'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out',
            'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
            'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will',
            'just', 'don', 'should', 'now'
        }
        
        # Sustainability-related keywords that should be prioritized
        self.sustainability_keywords = {
            'sustainability', 'sustainable', 'environment', 'environmental', 'climate', 'carbon', 'emission',
            'renewable', 'energy', 'solar', 'wind', 'green', 'eco', 'biodiversity', 'conservation',
            'recycling', 'waste', 'pollution', 'clean', 'esg', 'circular', 'economy', 'greenhouse',
            'mitigation', 'adaptation', 'resilience', 'efficiency', 'footprint', 'neutral', 'offset',
            'infrastructure', 'technology', 'innovation', 'policy', 'regulation', 'governance',
            'agriculture', 'farming', 'building', 'construction', 'transport', 'mobility', 'urban',
            'development', 'growth', 'impact', 'assessment', 'management', 'strategy', 'framework'
        }
    
    def generate_title(self, message: str, max_length: int = 50) -> str:
        """
        Generate a meaningful title from a user message.
        
        Args:
            message: The user's message
            max_length: Maximum length of the generated title
            
        Returns:
            Generated title
        """
        logger.info(f"TitleGenerator.generate_title called with message: '{message[:100]}...'")
        
        if not message or not message.strip():
            logger.info("TitleGenerator: Message empty, returning 'New Chat'")
            return "New Chat"
        
        # Clean and normalize the message
        cleaned_message = self._clean_message(message)
        logger.info(f"TitleGenerator: Cleaned message: '{cleaned_message[:100]}...'")
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(cleaned_message)
        logger.info(f"TitleGenerator: Extracted key phrases: {key_phrases}")
        
        # Generate title from key phrases
        title = self._create_title_from_phrases(key_phrases, max_length)
        
        # Fallback if no good title could be generated
        if not title or len(title.strip()) < 3:
            title = self._create_fallback_title(cleaned_message, max_length)
        
        logger.info(f"TitleGenerator: Final title generated: '{title}'")
        return title
    
    def _clean_message(self, message: str) -> str:
        """Clean and normalize the message."""
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', message.strip())
        
        # Remove common question starters
        cleaned = re.sub(r'^(what|how|why|when|where|who|can you|could you|please|tell me about|explain|describe)\s+', '', cleaned, flags=re.IGNORECASE)
        
        # Remove trailing question marks and other punctuation
        cleaned = re.sub(r'[?!.]+$', '', cleaned)
        
        return cleaned
    
    def _extract_key_phrases(self, message: str) -> list:
        """Extract key phrases from the message."""
        words = message.lower().split()
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if len(word) > 2 and word not in self.stop_words
        ]
        
        # Prioritize sustainability-related keywords
        sustainability_words = [word for word in filtered_words if word in self.sustainability_keywords]
        other_words = [word for word in filtered_words if word not in self.sustainability_keywords]
        
        # Combine with sustainability words first, but limit duplicates
        key_words = []
        seen = set()
        
        # Add sustainability words first (most important)
        for word in sustainability_words:
            if word not in seen:
                key_words.append(word)
                seen.add(word)
        
        # Add other meaningful words
        for word in other_words:
            if word not in seen and len(key_words) < 5:  # Limit to 5 words max
                key_words.append(word)
                seen.add(word)
        
        return key_words
    
    def _create_title_from_phrases(self, phrases: list, max_length: int) -> str:
        """Create a title from key phrases."""
        if not phrases:
            return ""
        
        # Remove duplicates while preserving order
        unique_phrases = []
        seen = set()
        for phrase in phrases:
            if phrase not in seen:
                unique_phrases.append(phrase)
                seen.add(phrase)
        
        # Create a more natural title structure
        if len(unique_phrases) >= 2:
            # Try to create a meaningful phrase
            if len(unique_phrases) >= 3:
                # Use first 3 words for better context
                title = " ".join(unique_phrases[:3]).title()
            else:
                # Use first 2 words
                title = " ".join(unique_phrases[:2]).title()
        else:
            # Single word - add context
            title = unique_phrases[0].title()
        
        # Ensure it's not too long
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title
    
    def _create_fallback_title(self, message: str, max_length: int) -> str:
        """Create a fallback title from the beginning of the message."""
        # Take the first few meaningful words (skip common question starters)
        words = message.split()
        
        # Skip common question starters
        skip_words = ['what', 'how', 'why', 'when', 'where', 'who', 'can', 'could', 'would', 'should', 'do', 'does', 'is', 'are', 'was', 'were']
        
        meaningful_words = []
        for word in words:
            if word.lower() not in skip_words and len(word) > 2:
                meaningful_words.append(word)
            if len(meaningful_words) >= 3:  # Take first 3 meaningful words
                break
        
        if not meaningful_words:
            # If no meaningful words found, take first 3 words
            meaningful_words = words[:3]
        
        title = " ".join(meaningful_words)
        
        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title.title() if title else "New Chat"


# Global title generator instance
title_generator = TitleGenerator()
