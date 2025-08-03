"""Configuration for enhanced AudioToText pipeline"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base configuration
BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')

# Directory configuration
PROJECT_ROOT = Path(__file__).parent
INPUT_FOLDER = os.getenv('INPUT_FOLDER', 'input_videos')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'output_audio')
TRANSCRIPTS_FOLDER = os.getenv('TRANSCRIPTS_FOLDER', 'transcripts')
KNOWLEDGE_BASE_FOLDER = os.getenv('KNOWLEDGE_BASE_FOLDER', 'knowledge_base')

# Model configuration
CONTEXT_MODEL = os.getenv('CONTEXT_MODEL', 'o3-mini')
ENHANCEMENT_MODEL = os.getenv('ENHANCEMENT_MODEL', 'gpt-4')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

# Weaviate configuration
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
OPENAI_APIKEY = os.getenv('OPENAI_APIKEY', os.getenv('API_KEY'))  # Fallback to API_KEY

# Processing configuration
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))  # For text chunking
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))   # For batch processing
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Feature flags
ENABLE_WEB_SEARCH = os.getenv('ENABLE_WEB_SEARCH', 'true').lower() == 'true'
ENABLE_FACT_CHECKING = os.getenv('ENABLE_FACT_CHECKING', 'true').lower() == 'true'
ENABLE_CROSS_REFERENCE = os.getenv('ENABLE_CROSS_REFERENCE', 'true').lower() == 'true'

# Validate required configuration
def validate_config():
    """Validate that required configuration is present"""
    errors = []
    
    if not BASE_URL:
        errors.append("BASE_URL not set in .env")
    if not API_KEY:
        errors.append("API_KEY not set in .env")
    
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    return True

# Create directories if they don't exist
def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        INPUT_FOLDER,
        OUTPUT_FOLDER,
        TRANSCRIPTS_FOLDER,
        KNOWLEDGE_BASE_FOLDER
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

if __name__ == "__main__":
    print("Configuration Summary:")
    print(f"  BASE_URL: {BASE_URL}")
    print(f"  Models: {CONTEXT_MODEL}, {ENHANCEMENT_MODEL}")
    print(f"  Weaviate: {WEAVIATE_URL}")
    print(f"  Features: search={ENABLE_WEB_SEARCH}, fact_check={ENABLE_FACT_CHECKING}")
    
    if validate_config():
        print("\n✅ Configuration valid!")
    else:
        print("\n❌ Configuration errors found!")