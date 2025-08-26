import dspy
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import re
 
# Import central configuration
from config import (
    OPENROUTER_API_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_API_BASE,
    DEFAULT_LLAMA_MODEL,
)

 
# --- Pydantic models for input and output ---
class ProviderExtractionInput(BaseModel):
    current_page_content: str = Field(..., description="Current page content with provider information")
    previous_page_content: Optional[str] = Field(None, description="Previous page content for context")
 
class ProviderData(BaseModel):
    provider_id_insurer: Optional[str] = None
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    practice_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None
    phone: Optional[str] = None
    languages: Optional[str] = None
    
 
class ProviderExtractionOutput(BaseModel):
    providers: List[ProviderData]
 
class ProviderExtractionSignature(dspy.Signature):
    """
    You are a specialized provider extraction system for Medicare Provider Directory documents.
    Your task is to extract ALL provider information from the provided page content and structure it according to the specified schema.
 
    ---------------------------
    ▶︎  OUTPUT JSON SCHEMA
    ---------------------------
    {
        "providers": [
            {
                "provider_id_insurer": <string or null>,     # PCP#, Provider ID, etc.
                "full_name": <string or null>,               # Full name as printed
                "specialty": <string or null>,               # Primary clinical focus
                "practice_name": <string or null>,           # Clinic/group name
                "address_line1": <string or null>,           # Street address line1
                "address_line2": <string or null>,           # Suite/building
                "city": <string or null>,                    # City name
                "state": <string or null>,                   # State code
                "zip": <string or null>,                     # ZIP code
                "county": <string or null>,                  # County name
                "phone": <string or null>,                   # Phone number
                "languages": <string or null>,               # Semicolon-separated languages
            }
        ]
    }
 
    ---------------------------
    ▶︎  EXTRACTION RULES
    ---------------------------
    1. **SYSTEMATIC PROVIDER IDENTIFICATION**
       - A provider *block starts whenever you encounter “Provider Name ” where name end with MD, DO etc as suffix*
         and ends **immediately befor another provider start.
       - While Reading the file . Read the file information vertically column wise, Block runs vertically.
       - The single provider information doesn't end till new provider name doesn't relfect
    1-a. **IGNORE NON-DATA LINES**: Discard headers, footers, disclaimers.
    2. **PROVIDER ID EXTRACTION**: Look for PCP#, Provider ID, etc.
    3. **NAME & CREDENTIALS**: Extract full name and credentials separately.
    4. **BOARD CERTIFICATION**: Flag true and extract board if indicated.
    5. **ADDRESS PARSING**: Split into line1/line2, city, state, zip. In some cases there can be multiple location addresses given. Extract all
    6. **SPECIAL FLAGS**: Medi-Cal, telehealth, age restrictions.
    7. **CONTACT & SERVICES**: Phone, telehealth modalities, languages, services.
    8. **NETWORK & PRACTICE**: Extract IPA/network and practice names.
    9. **CONTEXT UTILIZATION**: Use previous page for continuity.
    10. **QUALITY ASSURANCE**: Ensure at least an ID or name per provider.
    11. **Output only the JSON following schema above.**
    12. **DO NOT extract entries where the provider name contains words like "Center", "Clinic", "Group", "Hospital", "Network","SC" or "Health" — these are typically organization or facility names, not individual providers.**
 
 
    """
    current_page_content: str = dspy.InputField(desc="Current page content with provider information")
    previous_page_content: Optional[str] = dspy.InputField(desc="Previous page content for context")
 
    providers: List[Dict[str, Any]] = dspy.OutputField(
        desc="List of extracted providers with all available attributes"
    )
 
# --- Helper function to invoke DSPy chain ---
def extract_providers(
    current_page_content: str,
    previous_page_content: Optional[str] = None,
    specialty: Optional[str] = None,
    county: Optional[str] = None,
    model: str = DEFAULT_LLAMA_MODEL,
    api_key: str = OPENROUTER_API_KEY,
    api_base: str = OPENROUTER_API_BASE,
    api_url: str = OPENROUTER_API_URL,
    temperature: float = 0.1
) -> ProviderExtractionOutput:
    
    # Configure LM
    lm = dspy.LM(
        f"openrouter/{model}",
        api_key=api_key,
        api_base=api_base,
        max_tokens=10000,
        temperature=temperature,
        provider="openrouter",
    )
    dspy.configure(lm=lm)

    try:
        
        chain = dspy.ChainOfThought(ProviderExtractionSignature)

        # Process each page separately, passing previous page content as context
        
        result = chain(
            current_page_content=current_page_content,
            previous_page_content=previous_page_content or ""
        )
           
        # Validate and clean aggregated provider data
        valid_providers: List[ProviderData] = []
        for provider in result.providers:
            if not provider.get('provider_id_insurer') and not provider.get('full_name'):
                continue
            # Override county/specialty if missing
            if not provider.get("county"):
                provider["county"] = county
            if not provider.get("specialty"):
                provider["specialty"] = specialty
            valid_providers.append(ProviderData(**provider))

        return ProviderExtractionOutput(providers=valid_providers)

    except Exception as e:
        print(f"Error in provider extraction: {str(e)}")
        return ProviderExtractionOutput(providers=[])