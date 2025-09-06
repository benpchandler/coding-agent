#!/usr/bin/env python3
"""
Simple script to help set up the OpenAI API key for the Coding Agent system.
"""

import os
import sys
from pathlib import Path

def main():
    print("🤖 Coding Agent - API Key Setup")
    print("=" * 40)
    
    # Check if .env already exists
    env_file = Path('.env')
    if env_file.exists():
        print("✓ .env file already exists")
        with open(env_file, 'r') as f:
            content = f.read()
            if 'OPENAI_API_KEY=' in content and 'your-openai-api-key-here' not in content:
                print("✓ API key appears to be configured in .env file")
                return
    
    print("\nOptions for setting up your OpenAI API key:")
    print("1. Create .env file (recommended for development)")
    print("2. Use web dashboard (secure encrypted storage)")
    print("3. Set environment variable manually")
    
    choice = input("\nChoose an option (1-3): ").strip()
    
    if choice == '1':
        setup_env_file()
    elif choice == '2':
        setup_web_dashboard()
    elif choice == '3':
        setup_environment_variable()
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

def setup_env_file():
    """Set up .env file"""
    print("\n📝 Setting up .env file...")
    
    api_key = input("Enter your OpenAI API key (starts with sk-): ").strip()
    
    if not api_key:
        print("❌ API key cannot be empty")
        sys.exit(1)
    
    if not api_key.startswith('sk-'):
        print("❌ Invalid API key format. OpenAI API keys start with 'sk-'")
        sys.exit(1)
    
    env_content = f"""# OpenAI API Configuration
OPENAI_API_KEY={api_key}

# Optional: Model configuration
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    # Make .env file readable only by owner
    os.chmod('.env', 0o600)
    
    print("✅ .env file created successfully!")
    print("🔒 File permissions set to owner-only for security")
    print("\nYou can now run the system:")
    print("  python main.py")
    print("  python web_dashboard.py")

def setup_web_dashboard():
    """Guide user to web dashboard setup"""
    print("\n🌐 Web Dashboard Setup")
    print("1. Start the web dashboard: python web_dashboard.py")
    print("2. Open your browser to http://localhost:8000")
    print("3. Click 'API Settings' in the navigation")
    print("4. Enter your OpenAI API key in the form")
    print("5. The key will be encrypted and stored securely")

def setup_environment_variable():
    """Guide user to set environment variable"""
    print("\n🔧 Environment Variable Setup")
    print("Set the OPENAI_API_KEY environment variable:")
    print("\nFor current session:")
    print("  export OPENAI_API_KEY='your-api-key-here'")
    print("\nFor permanent setup, add to your shell profile:")
    print("  echo 'export OPENAI_API_KEY=\"your-api-key-here\"' >> ~/.bashrc")
    print("  echo 'export OPENAI_API_KEY=\"your-api-key-here\"' >> ~/.zshrc")

if __name__ == "__main__":
    main()
