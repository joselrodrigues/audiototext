#!/usr/bin/env python3
"""Diagnostic script to check configuration and connections"""

import os
import sys
from dotenv import load_dotenv
import requests
from openai import OpenAI

def check_env_file():
    """Check if .env file exists and is properly configured"""
    print("🔍 Checking .env file...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("   Create a .env file with:")
        print("   BASE_URL=your_llm_service_url")
        print("   API_KEY=your_api_key")
        return False
    
    print("✅ .env file found")
    
    # Load environment variables
    load_dotenv()
    
    base_url = os.getenv('BASE_URL')
    api_key = os.getenv('API_KEY')
    
    if not base_url:
        print("❌ BASE_URL not set in .env file")
        return False
    print(f"✅ BASE_URL: {base_url}")
    
    if not api_key:
        print("❌ API_KEY not set in .env file")
        return False
    print("✅ API_KEY is set")
    
    return True

def test_connection():
    """Test connection to the LLM service"""
    print("\n🔍 Testing LLM service connection...")
    
    load_dotenv()
    base_url = os.getenv('BASE_URL')
    api_key = os.getenv('API_KEY')
    
    if not base_url or not api_key:
        print("❌ Missing configuration")
        return False
    
    try:
        # Test basic HTTP connectivity
        print(f"   Testing HTTP connectivity to {base_url}...")
        response = requests.get(base_url, timeout=10)
        print(f"   HTTP Status: {response.status_code}")
        
        # Test OpenAI client
        print("   Testing OpenAI client...")
        client = OpenAI(base_url=base_url, api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or whatever model you're using
            messages=[{"role": "user", "content": "Hello, this is a test"}],
            max_tokens=10
        )
        
        print("✅ LLM service connection successful!")
        print(f"   Response: {response.choices[0].message.content}")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the service (Connection Error)")
        print("   Check if the service is running")
        print("   Verify the BASE_URL is correct")
        return False
    except requests.exceptions.Timeout:
        print("❌ Connection timeout")
        print("   The service might be slow or overloaded")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)[:200]}")
        return False

def check_directories():
    """Check if required directories exist"""
    print("\n🔍 Checking directories...")
    
    required_dirs = ['transcripts', 'knowledge_base']
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ directory exists")
            # Count files
            files = []
            for root, dirs, filenames in os.walk(dir_name):
                for filename in filenames:
                    if filename.endswith('.md'):
                        files.append(os.path.join(root, filename))
            print(f"   Found {len(files)} .md files")
        else:
            print(f"⚠️  {dir_name}/ directory not found (will be created as needed)")

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        'openai',
        'langgraph', 
        'python-dotenv',
        'requests',
        'langchain_mcp_adapters'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} not installed")
            print(f"   Install with: uv add {package}")

def main():
    """Run all diagnostic checks"""
    print("🩺 AudioToText Diagnostics\n")
    print("=" * 50)
    
    env_ok = check_env_file()
    check_dependencies()
    check_directories()
    
    if env_ok:
        connection_ok = test_connection()
        
        if connection_ok:
            print("\n🎉 All checks passed! Your system should work correctly.")
        else:
            print("\n⚠️  Configuration issues detected. Please fix the connection problems.")
    else:
        print("\n⚠️  Environment configuration issues detected. Please fix .env file.")
    
    print("\n" + "=" * 50)
    print("If you need help, check the README.md file or create an issue.")

if __name__ == "__main__":
    main()