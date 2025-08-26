import re
from typing import Tuple

import re
from typing import Tuple, List

def clean_provider_markdown(raw_markdown: str, max_tokens_per_chunk: int = 1000) -> Tuple[List[str], str, str]:
    # ✅ Enhanced cleaner to normalize content
    def clean_line(line: str) -> str:
        line = re.sub(r'^\*+\s*', '', line)
        line = re.sub(r'\s*\*+$', '', line)
        line = line.replace('\u200b', '')
        line = re.sub(r'\s{2,}', ' ', line)
        return line.strip()

    def is_page_break(line):
        return (
            re.match(r'^(\*+)?\s*Board Certified Provider', line, re.IGNORECASE)
            or re.match(r'^PRIMARY CARE PROVIDERS$', line, re.IGNORECASE)
            or re.match(r'^\d+$', line.strip())
            or re.match(r'^-{3,}$', line.strip())
            or re.match(r'^#.*Primary Care Providers', line.strip(), re.IGNORECASE)
            or re.match(r'^## Page \d+', line.strip(), re.IGNORECASE)
        )

    def is_provider_name(line):
        return re.match(r'^[*]*[A-Z][^,]+, .+\b(MD|DO|SC)[*]*$', line.strip())

    def bold_if_needed(line):
        clean = line.strip('* ').strip()
        if re.search(r'\b(MD|DO|SC)$', clean):
            return f"**{clean}**"
        return clean

    county_match = re.search(r'##\s*([A-Z\s]+) COUNTY', raw_markdown, re.IGNORECASE)
    specialty_match = re.search(r'####?\s*(.+PCP.+)', raw_markdown, re.IGNORECASE)

    county = county_match.group(1).title().strip() + " County" if county_match else None
    specialty = specialty_match.group(1).strip() if specialty_match else None

    lines = raw_markdown.splitlines()
    buffer = []
    providers = []
    current_provider = None

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line or is_page_break(line):
            continue

        if county and re.match(r'^##\s*' + re.escape(county.split()[0]), line, re.IGNORECASE):
            continue
        if specialty and re.match(r'^###?\s*' + re.escape(specialty.split()[0]), line, re.IGNORECASE):
            continue
        if re.match(r'^#', line):  # remove headings
            continue

        if is_provider_name(line):
            if current_provider:
                providers.append(current_provider)
            current_provider = {
                'name': bold_if_needed(line),
                'info': []
            }
        else:
            if current_provider:
                current_provider['info'].append(line)
            else:
                buffer.append(line)

    if current_provider:
        providers.append(current_provider)

    def format_provider(p):
        return "\n".join([p['name']] + p['info']) + "\n"

    def count_tokens(text: str) -> int:
        return len(text.split())

    chunks = []
    current_chunk = ""
    current_token_count = 0

    for provider in providers:
        provider_text = format_provider(provider)
        provider_tokens = count_tokens(provider_text)

        if current_token_count + provider_tokens > max_tokens_per_chunk:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = provider_text
            current_token_count = provider_tokens
        else:
            current_chunk += provider_text
            current_token_count += provider_tokens
    

    if current_chunk:
      
        chunks.append(current_chunk.strip())

    return chunks, county, specialty