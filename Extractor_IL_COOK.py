import dspy
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Configuration (replace with your actual config) ---
from config import (
    OPENROUTER_API_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_API_BASE,
    DEFAULT_LLAMA_MODEL,
)

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

# --- Signature with instructions ---
class ProviderExtractionSignature(dspy.Signature):
    """
    You are a specialized provider extraction system for Medicare Provider Directory documents.

Your task is to extract ALL provider information from the provided page content and structure it exactly according to the specified JSON schema.

───────────────────────────────
▶︎ OUTPUT JSON SCHEMA
───────────────────────────────
{
    "providers": [
        {
            "provider_id_insurer": <string or null>,
            "full_name": <string or null>,
            "specialty": <string or null>,
            "practice_name": <string or null>,
            "address_line1": <string or null>,
            "address_line2": <string or null>,
            "city": <string or null>,
            "state": <string or null>,
            "zip": <string or null>,
            "county": <string or null>,
            "phone": <string or null>,
            "languages": <string or null>
        }
    ]
}

───────────────────────────────
▶︎ BLOCK DEFINITION
───────────────────────────────

- An organization block starts with a line containing the organization/practice name (e.g., "Advocate Medical Group").
- The block includes all subsequent lines until the next organization/practice name line.
- All providers and address info within this block belong to the organization.
- Extract providers, addresses, phones, and other info grouped under that organization.

───────────────────────────────
▶︎ EXTRACTION RULES
───────────────────────────────

1. Organization names include keywords like: Center, Clinic, Health, Hospital, Medical, Network, Group, Access, SC, Ltd, Inc, etc.
   - These should NOT be extracted as individual providers.
   - They act as `practice_name` for all providers beneath them.
   - However, if no provider is listed, still return the organization and its address with `"full_name": null`.

2. Organizations (practice_name) can have their own PCP# or IDs.
   - Extract organizations as entries with `"full_name": null` and their PCP# as `"provider_id_insurer"`.
   - Providers under them have `"full_name"` and their own PCP#.
   - Do not merge organization PCP# with any provider unless explicitly the same.

3. Provider entries:
   - Recognized by names ending with `MD`, `DO`, etc. (NOT SC).
   - Names ending with SC indicate an organization, NOT a provider.
   - Provider data blocks may span multiple lines (e.g., PCP#, languages, certifications).
   - Assign the address and organization as their `practice_name` present in the affliated block.

4. Address blocks:
   - Begin with a numeric street address.
   - Include optional suite, city, state, zip, and phone.

5. If a block contains an organization name with one or more addresses but **no providers listed**,  
   you **must still output an entry** with:  
   - `"full_name": null`  
   - `"practice_name"` set to the organization name  
   - all associated address fields populated  
   - phone number(s) if available  
   - other fields set to `null` as applicable.

6. Phone numbers may appear near provider or address; match them to the correct level (organization or provider).

7. Output must contain only valid JSON matching the schema.
   - Use `null` for any missing fields.
   - Use `;` as a separator for multiple languages if present.

8. Ignore page headers, footers, disclaimers, and organizations in the `"full_name"` field.

───────────────────────────────
▶︎ EXAMPLES
───────────────────────────────
- "Jarava, Abelardo MD" is a provider under "Abelardo J Jarava MD SC"
- "7 Hills HealthCare Center" with no provider should still be returned with `"full_name": null`
- "Access Genesis Center for Health and Empowerment" with PCP# 138567 and no provider name is an organization entry.
- "Patel, Nigam M MD*" with PCP# 138567 under that organization is a provider entry.
- An organization like "**Adventist Health Partners Inc**" with addresses and no providers should output entries with `"full_name": null` but all address fields and phone numbers included.

───────────────────────────────
▶︎ REMINDER
───────────────────────────────
Output ONLY the JSON matching schema.  
No explanations. No extra text.

    """

    current_page_content: str = dspy.InputField(desc="Current page content with provider information")
    previous_page_content: Optional[str] = dspy.InputField(desc="Previous page content for continuity")

    providers: List[Dict[str, Any]] = dspy.OutputField(
        desc="List of extracted providers with all available attributes"
    )

# --- Helper function ---
def propagate_org_phone(providers: List[Dict]) -> List[Dict]:
    # Map (practice_name, address_line1) -> phone from org entries
    org_phones = {}
    for p in providers:
        key = (p.get("practice_name"), p.get("address_line1"))
        if p.get("full_name") is None and p.get("phone"):
            org_phones[key] = p["phone"]

    # Fill provider phones if missing
    for p in providers:
        key = (p.get("practice_name"), p.get("address_line1"))
        if p.get("full_name") and not p.get("phone"):
            p["phone"] = org_phones.get(key)

    return providers


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
    lm = dspy.LM(
        f"openrouter/{model}",
        api_key=api_key,
        api_base=api_base,
        max_tokens=10000,
        provider="openrouter",
        
        temperature=temperature,
    )
    dspy.configure(lm=lm)

    try:
        chain = dspy.ChainOfThought(ProviderExtractionSignature)
        result = chain(
            current_page_content=current_page_content,
            previous_page_content=previous_page_content or ""
        )

        # Validate and clean providers
        valid_providers: List[Dict] = []
        for provider in result.providers:
            if not provider.get('provider_id_insurer') and not provider.get('full_name') and not provider.get('practice_name'):
                continue
            valid_providers.append(provider)

        # Propagate org phone numbers to providers
        valid_providers = propagate_org_phone(valid_providers)

        # Convert dicts to Pydantic models
        provider_models = [ProviderData(**p) for p in valid_providers]
        for p in provider_models:
            p.specialty = specialty
            p.county = county

        return ProviderExtractionOutput(providers=provider_models)

    except Exception as e:
        print(f"Error in provider extraction: {str(e)}")
        return ProviderExtractionOutput(providers=[])