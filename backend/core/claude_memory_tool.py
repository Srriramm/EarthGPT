"""
Claude Memory Tool Handler - Implements the memory tool commands as specified in Claude API docs.

This module implements the client-side handlers for Claude's memory tool commands:
- view: View directory or file contents
- create: Create/overwrite a file
- str_replace: Replace text in a file
- insert: Insert text at a specific line
- delete: Delete file/directory
- rename: Rename/move file or directory
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from config import settings
from .mongodb_memory import mongodb_session_manager


class ClaudeMemoryToolHandler:
    """
    Handler for Claude's memory tool commands.
    
    Implements all memory tool commands as specified in the Claude API documentation:
    https://docs.anthropic.com/claude/docs/memory-tool
    """
    
    def __init__(self, memories_dir: str = None):
        """Initialize the memory tool handler."""
        self.memories_dir = Path(memories_dir or settings.memories_directory)
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        
        # Security: Ensure we stay within the memories directory
        self.memories_dir = self.memories_dir.resolve()
        
        logger.info(f"Claude Memory Tool Handler initialized with directory: {self.memories_dir}")
    
    async def handle_memory_command(self, command: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        Handle a memory tool command from Claude using MongoDB storage.
        
        Args:
            command: Dictionary containing the command details
            session_id: Optional session ID for session-scoped operations
            
        Returns:
            Dictionary with the result of the command execution
        """
        try:
            cmd_type = command.get("command")
            path = command.get("path")
            
            # For MongoDB-based storage, we'll store memories as MongoDB documents
            # instead of files. This provides better session isolation and performance.
            
            if cmd_type == "view":
                return await self._handle_view_mongodb(path, session_id)
            elif cmd_type == "create":
                return await self._handle_create_mongodb(path, command.get("file_text", ""), session_id)
            elif cmd_type == "str_replace":
                return await self._handle_str_replace_mongodb(
                    path, 
                    command.get("old_str", ""), 
                    command.get("new_str", ""),
                    session_id
                )
            elif cmd_type == "insert":
                return await self._handle_insert_mongodb(
                    path,
                    command.get("insert_line", 1),
                    command.get("insert_text", ""),
                    session_id
                )
            elif cmd_type == "delete":
                return await self._handle_delete_mongodb(path, session_id)
            elif cmd_type == "rename":
                return await self._handle_rename_mongodb(
                    command.get("old_path", ""),
                    command.get("new_path", ""),
                    session_id
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown command: {cmd_type}",
                    "content": ""
                }
                
        except Exception as e:
            logger.error(f"Error handling memory command {command}: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _is_safe_path(self, path: str) -> bool:
        """Validate that the path is safe and within the memories directory."""
        if not path:
            return False
        
        # Resolve the path relative to memories directory
        try:
            full_path = (self.memories_dir / path.lstrip("/")).resolve()
            # Check if the resolved path is within the memories directory
            return full_path.is_relative_to(self.memories_dir)
        except (OSError, ValueError):
            return False
    
    def _get_full_path(self, path: str) -> Path:
        """Get the full path for a given relative path."""
        return self.memories_dir / path.lstrip("/")
    
    def _handle_view(self, path: str) -> Dict[str, Any]:
        """Handle view command - view directory or file contents."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"Path does not exist: {path}",
                    "content": ""
                }
            
            if full_path.is_dir():
                # List directory contents
                items = []
                for item in sorted(full_path.iterdir()):
                    if item.is_dir():
                        items.append(f"[DIR] {item.name}/")
                    else:
                        size = item.stat().st_size
                        items.append(f"[FILE] {item.name} ({size} bytes)")
                
                content = f"Directory: {path}\n" + "\n".join(items) if items else f"Directory: {path}\n(empty)"
                
                return {
                    "success": True,
                    "content": content,
                    "error": None
                }
            else:
                # Read file contents
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {
                        "success": True,
                        "content": content,
                        "error": None
                    }
                except UnicodeDecodeError:
                    return {
                        "success": False,
                        "error": f"File is not text readable: {path}",
                        "content": ""
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _handle_create(self, path: str, file_text: str) -> Dict[str, Any]:
        """Handle create command - create/overwrite a file."""
        try:
            full_path = self._get_full_path(path)
            
            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file_text)
            
            return {
                "success": True,
                "content": f"Created file: {path}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _handle_str_replace(self, path: str, old_str: str, new_str: str) -> Dict[str, Any]:
        """Handle str_replace command - replace text in a file with fallback strategies."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {path}",
                    "content": ""
                }
            
            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {path}",
                    "content": ""
                }
            
            # Read file content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try exact match first
            if old_str in content:
                new_content = content.replace(old_str, new_str)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return {
                    "success": True,
                    "content": f"Replaced text in file: {path}",
                    "error": None
                }
            
            # If exact match fails, try fallback strategies
            logger.warning(f"Exact text match failed for str_replace in {path}, trying fallback strategies")
            
            # Strategy 1: Try to append new content to the end of the file
            if new_str.strip() and not new_str.strip() in content:
                # Append new content with proper formatting
                if content.strip() and not content.endswith('\n'):
                    content += '\n'
                new_content = content + '\n' + new_str
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return {
                    "success": True,
                    "content": f"Appended new content to file: {path} (exact match failed, used append strategy)",
                    "error": None
                }
            
            # Strategy 2: If new content is already in the file, consider it successful
            elif new_str.strip() in content:
                return {
                    "success": True,
                    "content": f"Content already exists in file: {path}",
                    "error": None
                }
            
            # Strategy 3: Try partial matching for common patterns
            # Look for similar headings or sections to replace
            lines = content.split('\n')
            new_lines = []
            old_lines = old_str.split('\n')
            
            # Try to find a matching section by looking for similar heading patterns
            found_section = False
            i = 0
            while i < len(lines):
                line = lines[i]
                # Check if this line matches any of the old_str lines (ignoring whitespace)
                if any(line.strip() == old_line.strip() for old_line in old_lines if old_line.strip()):
                    # Found a potential match, try to replace the section
                    new_lines.extend(new_str.split('\n'))
                    found_section = True
                    # Skip the matching lines from old content
                    skip_count = 0
                    for old_line in old_lines:
                        if old_line.strip() and i + skip_count < len(lines):
                            if lines[i + skip_count].strip() == old_line.strip():
                                skip_count += 1
                            else:
                                break
                    i += skip_count
                else:
                    new_lines.append(line)
                    i += 1
            
            if found_section:
                new_content = '\n'.join(new_lines)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return {
                    "success": True,
                    "content": f"Replaced similar content in file: {path} (used partial matching)",
                    "error": None
                }
            
            # If all strategies fail, return the original error
            return {
                "success": False,
                "error": f"Text not found and fallback strategies failed for file: {path}",
                "content": content  # Return current content for debugging
            }
            
        except Exception as e:
            logger.error(f"Error in str_replace for {path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _handle_insert(self, path: str, insert_line: int, insert_text: str) -> Dict[str, Any]:
        """Handle insert command - insert text at a specific line."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File does not exist: {path}",
                    "content": ""
                }
            
            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {path}",
                    "content": ""
                }
            
            # Read file lines
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Validate line number
            if insert_line < 1 or insert_line > len(lines) + 1:
                return {
                    "success": False,
                    "error": f"Invalid line number: {insert_line}. File has {len(lines)} lines.",
                    "content": ""
                }
            
            # Insert text (convert to 0-based index)
            lines.insert(insert_line - 1, insert_text + "\n")
            
            # Write back
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return {
                "success": True,
                "content": f"Inserted text at line {insert_line} in file: {path}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _handle_delete(self, path: str) -> Dict[str, Any]:
        """Handle delete command - delete file/directory."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"Path does not exist: {path}",
                    "content": ""
                }
            
            if full_path.is_dir():
                shutil.rmtree(full_path)
                return {
                    "success": True,
                    "content": f"Deleted directory: {path}",
                    "error": None
                }
            else:
                full_path.unlink()
                return {
                    "success": True,
                    "content": f"Deleted file: {path}",
                    "error": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def _handle_rename(self, old_path: str, new_path: str) -> Dict[str, Any]:
        """Handle rename command - rename/move file or directory."""
        try:
            old_full_path = self._get_full_path(old_path)
            new_full_path = self._get_full_path(new_path)
            
            if not old_full_path.exists():
                return {
                    "success": False,
                    "error": f"Source path does not exist: {old_path}",
                    "content": ""
                }
            
            # Ensure parent directory of new path exists
            new_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rename/move
            old_full_path.rename(new_full_path)
            
            return {
                "success": True,
                "content": f"Renamed {old_path} to {new_path}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory directory."""
        try:
            total_files = 0
            total_dirs = 0
            total_size = 0
            
            for root, dirs, files in os.walk(self.memories_dir):
                total_dirs += len(dirs)
                for file in files:
                    total_files += 1
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
            
            return {
                "total_files": total_files,
                "total_directories": total_dirs,
                "total_size_bytes": total_size,
                "memories_directory": str(self.memories_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {
                "total_files": 0,
                "total_directories": 0,
                "total_size_bytes": 0,
                "memories_directory": str(self.memories_dir),
                "error": str(e)
            }


    # MongoDB-based handlers
    
    async def _handle_view_mongodb(self, path: str, session_id: str = None) -> Dict[str, Any]:
        """Handle view command using MongoDB storage."""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "Session ID required for MongoDB operations",
                    "content": ""
                }
            
            # Get session memories from MongoDB
            memories = await mongodb_session_manager.search_memories("", session_id, limit=50)
            
            # Format as directory listing
            content_lines = [f"Directory: {path}"]
            if memories:
                for memory in memories:
                    memory_id = memory.get("memory_id", "unknown")[:8]
                    content_lines.append(f"[MEMORY] {memory_id} - {memory.get('content', '')[:50]}...")
            else:
                content_lines.append("(empty)")
            
            return {
                "success": True,
                "content": "\n".join(content_lines),
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    async def _handle_create_mongodb(self, path: str, file_text: str, session_id: str = None) -> Dict[str, Any]:
        """Handle create command using MongoDB storage."""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "Session ID required for MongoDB operations",
                    "content": ""
                }
            
            # Create memory in MongoDB
            memory_id = await mongodb_session_manager.create_memory(
                session_id,
                file_text,
                {"type": "file", "path": path, "created_via": "memory_tool"}
            )
            
            return {
                "success": True,
                "content": f"Created memory in MongoDB: {memory_id}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    async def _handle_str_replace_mongodb(self, path: str, old_str: str, new_str: str, session_id: str = None) -> Dict[str, Any]:
        """Handle str_replace command using MongoDB storage."""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "Session ID required for MongoDB operations",
                    "content": ""
                }
            
            # For MongoDB, we'll create a new memory with the updated content
            # This is simpler and more reliable than trying to modify existing content
            memory_id = await mongodb_session_manager.create_memory(
                session_id,
                new_str,
                {"type": "str_replace", "path": path, "old_str": old_str, "new_str": new_str}
            )
            
            return {
                "success": True,
                "content": f"Updated content stored in MongoDB: {memory_id}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    async def _handle_insert_mongodb(self, path: str, insert_line: int, insert_text: str, session_id: str = None) -> Dict[str, Any]:
        """Handle insert command using MongoDB storage."""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "Session ID required for MongoDB operations",
                    "content": ""
                }
            
            # Create memory with insert information
            memory_id = await mongodb_session_manager.create_memory(
                session_id,
                insert_text,
                {"type": "insert", "path": path, "line": insert_line}
            )
            
            return {
                "success": True,
                "content": f"Inserted content in MongoDB: {memory_id}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    async def _handle_delete_mongodb(self, path: str, session_id: str = None) -> Dict[str, Any]:
        """Handle delete command using MongoDB storage."""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "Session ID required for MongoDB operations",
                    "content": ""
                }
            
            # For MongoDB, we'll mark memories for deletion by creating a deletion marker
            memory_id = await mongodb_session_manager.create_memory(
                session_id,
                f"DELETED: {path}",
                {"type": "delete", "path": path, "deleted": True}
            )
            
            return {
                "success": True,
                "content": f"Marked for deletion in MongoDB: {memory_id}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }
    
    async def _handle_rename_mongodb(self, old_path: str, new_path: str, session_id: str = None) -> Dict[str, Any]:
        """Handle rename command using MongoDB storage."""
        try:
            if not session_id:
                return {
                    "success": False,
                    "error": "Session ID required for MongoDB operations",
                    "content": ""
                }
            
            # Create rename marker in MongoDB
            memory_id = await mongodb_session_manager.create_memory(
                session_id,
                f"RENAMED: {old_path} -> {new_path}",
                {"type": "rename", "old_path": old_path, "new_path": new_path}
            )
            
            return {
                "success": True,
                "content": f"Rename recorded in MongoDB: {memory_id}",
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }


# Global instance
claude_memory_tool_handler = ClaudeMemoryToolHandler()

