#!/usr/bin/env python3
"""
EarthGPT Setup Script
Sets up both backend and frontend for the EarthGPT application
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description, cwd=None):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            cwd=cwd,
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python():
    """Check Python installation."""
    print(f"🐍 Python version: {sys.version}")
    return True

def check_node():
    """Check Node.js installation."""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"📦 Node.js version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js from https://nodejs.org/")
        return False

def setup_backend():
    """Set up the Python backend."""
    print("\n🔧 Setting up EarthGPT Backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies", cwd=backend_dir):
        return False
    
    # Create necessary directories
    directories = ["logs", "chroma_db", "models"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    print("✅ Backend setup completed")
    return True

def setup_frontend():
    """Set up the React frontend."""
    print("\n🎨 Setting up EarthGPT Frontend...")
    
    frontend_dir = Path("frontend")
    
    # Check if frontend directory exists
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    # Install Node.js dependencies
    if not run_command("npm install --legacy-peer-deps", "Installing Node.js dependencies", cwd=frontend_dir):
        return False
    
    print("✅ Frontend setup completed")
    return True

def test_setup():
    """Test the setup by running basic checks."""
    print("\n🧪 Testing setup...")
    
    # Test Python imports
    try:
        import fastapi
        import uvicorn
        import transformers
        print("✅ Python dependencies working")
    except ImportError as e:
        print(f"❌ Python import error: {e}")
        return False
    
    # Test Node.js setup
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        node_modules = frontend_dir / "node_modules"
        if node_modules.exists():
            print("✅ Node.js dependencies installed")
        else:
            print("❌ Node.js dependencies not found")
            return False
    
    print("✅ Setup test completed")
    return True

def main():
    """Main setup function."""
    print("🌱 EarthGPT Setup")
    print("=" * 50)
    
    # Check prerequisites
    if not check_python():
        print("❌ Python check failed")
        return
    
    if not check_node():
        print("❌ Node.js check failed")
        return
    
    # Setup backend
    if not setup_backend():
        print("❌ Backend setup failed")
        return
    
    # Setup frontend
    if not setup_frontend():
        print("❌ Frontend setup failed")
        return
    
    # Test setup
    if not test_setup():
        print("❌ Setup test failed")
        return
    
    print("\n🎉 EarthGPT setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start the application: python start_earthgpt.py")
    print("2. Or start manually:")
    print("   - Backend: cd backend && python main.py")
    print("   - Frontend: cd frontend && npm start")
    print("\n🌐 URLs:")
    print("- Frontend: http://localhost:3000")
    print("- Backend: http://localhost:8000")
    print("- API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
