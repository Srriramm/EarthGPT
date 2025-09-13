#!/usr/bin/env python3
"""
EarthGPT Startup Script
Starts both the FastAPI backend and React frontend
"""

import subprocess
import sys
import time
import threading
import os
from pathlib import Path

def run_backend():
    """Start the FastAPI backend server."""
    print("🚀 Starting EarthGPT Backend...")
    backend_dir = Path("backend")
    
    if not backend_dir.exists():
        print("❌ Backend directory not found. Please run the setup first.")
        return
    
    try:
        # Change to backend directory and start the server
        os.chdir(backend_dir)
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ Backend stopped")
    except Exception as e:
        print(f"❌ Backend error: {e}")

def run_frontend():
    """Start the React frontend development server."""
    print("🎨 Starting EarthGPT Frontend...")
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found. Please run the setup first.")
        return
    
    try:
        # Change to frontend directory and start React app
        os.chdir(frontend_dir)
        subprocess.run(["npm", "start"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ Frontend stopped")
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js and npm first.")
    except Exception as e:
        print(f"❌ Frontend error: {e}")

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    # Check Python dependencies
    try:
        import fastapi
        import uvicorn
        print("✅ Python dependencies OK")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("Please run: pip install -r backend/requirements.txt")
        return False
    
    # Check Node.js and npm
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js {result.stdout.strip()}")
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js first.")
        return False
    
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm {result.stdout.strip()}")
        else:
            print("❌ npm not found")
            return False
    except FileNotFoundError:
        print("❌ npm not found. Please install npm first.")
        return False
    
    # Check if frontend dependencies are installed
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("⚠️ Frontend dependencies not installed. Installing...")
            try:
                os.chdir(frontend_dir)
                subprocess.run(["npm", "install"], check=True)
                os.chdir("..")
                print("✅ Frontend dependencies installed")
            except Exception as e:
                print(f"❌ Failed to install frontend dependencies: {e}")
                return False
    
    return True

def main():
    """Main startup function."""
    print("🌱 EarthGPT - Sustainability AI Assistant")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing dependencies.")
        return
    
    print("\n📋 Starting EarthGPT...")
    print("Backend will run on: http://localhost:8000")
    print("Frontend will run on: http://localhost:3000")
    print("API Documentation: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both servers")
    print("=" * 50)
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend in main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\n👋 EarthGPT stopped. Thank you!")

if __name__ == "__main__":
    main()
