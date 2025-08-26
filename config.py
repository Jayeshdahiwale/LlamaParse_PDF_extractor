import os
from pathlib import Path
from dotenv import load_dotenv
 
# Load environment variables from .env file
load_dotenv()
 
# Get the base directory (the root folder of your project)
BASE_DIR = Path(__file__).resolve().parent
 
# File & parser settings
PDF_PATH       = os.getenv("PDF_PATH")                       # Can be None if not passed
OUTPUT_PATH    = os.getenv("OUTPUT_PATH")                    # Can be None if not passed
PARSER_TYPE    = os.getenv("PARSER", "pdfplumber")
 
# API Keys
LLAMA_API_KEY  = os.getenv("LLAMA_API_KEY")
 
# Batching & storage
BATCH_SIZE     = int(os.getenv("BATCH_SIZE", "10"))
STORE_INTERVAL = int(os.getenv("STORE_INTERVAL", "5"))  # in seconds
 
# OpenRouter API (if using LLMs from OpenRouter)
OPENROUTER_API_URL   = os.getenv("OPENROUTER_API_URL")
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_BASE  = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
DEFAULT_LLAMA_MODEL  = os.getenv("DEFAULT_LLAMA_MODEL", "google/gemini-2.0-flash-001")
 
# Prompt file paths (relative to the project)
PROMPT_IL_COOK = str(BASE_DIR / "prompts" / "IL_COOK_prompt.txt")
PROMPT_CA_LA   = str(BASE_DIR / "prompts" / "CA_LA_prompt.txt")