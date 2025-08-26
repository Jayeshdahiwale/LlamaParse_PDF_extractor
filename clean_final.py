import re
from typing import Tuple, List, Optional

def clean_provider_markdown_unified(
    raw_markdown: str,
    source_format: str,  # e.g., "ca_la", "il_cook", "ny_queens" etc.
    max_tokens_or_chars: int = 1000
) -> Tuple[List[str], Optional[str], Optional[str]]:
    
    def is_page_break(line):
        return (
            re.match(r'^(\*+)?\s*Board Certified Provider', line.strip(), re.IGNORECASE)
            or re.match(r'^PRIMARY CARE PROVIDERS$', line.strip(), re.IGNORECASE)
            or re.match(r'^\d+$', line.strip())
            or re.match(r'^-{3,}$', line.strip())
            or re.match(r'^#.*Primary Care Providers', line.strip(), re.IGNORECASE)
            or re.match(r'^## Page \d+', line.strip(), re.IGNORECASE)
        )

    def clean_line(line: str) -> str:
        line = re.sub(r'^\*+\s*', '', line)
        line = re.sub(r'\s*\*+$', '', line)
        line = line.replace('\u200b', '')
        line = re.sub(r'\s{2,}', ' ', line)
        return line.strip()

    def is_provider_name(line):
        return re.match(r'^[*]*[A-Z][^,]+, .+\b(MD|DO|SC)[*]*$', line.strip())

    def bold_if_needed(line):
        clean = line.strip('* ').strip()
        if re.search(r'\b(MD|DO|SC)$', clean):
            return f"**{clean}**"
        return clean

    def is_org_name(line):
        org_keywords = r'(Center|Clinic|Health|Hospital|Medical|Access|Sinai|Group|SC|Ltd|Midwest|Partners|Associates|Network)'
        return bool(re.search(org_keywords, line.strip(), re.IGNORECASE))

    def remove_bold(line):
        return re.sub(r'^\*{1,2}(.*?)\*{1,2}$', r'\1', line.strip())

    def remove_header_hashes(line):
        return re.sub(r'^#{1,6}\s*', '', line).strip()

    def is_street_address(line):
        return re.match(r'^\d{3,5}\s+[\w\s.]+', line.strip())

    def is_phone_number(line):
        return re.match(r'^\(\d{3}\)\s*\d{3}-\d{4}$', line.strip())

    # Extract metadata
    county_match = re.search(r'###\s*([A-Z\s]+ COUNTY)', raw_markdown, re.IGNORECASE)
    specialty_match = re.search(r'####?\s*(.+)', raw_markdown)

    county = county_match.group(1).title().strip() if county_match else None
    specialty = specialty_match.group(1).strip() if specialty_match else None

    # === FORMAT A: CA_LA-style ===
    if source_format.lower() == "ca_la":
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
            if re.match(r'^#', line):
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

            if current_token_count + provider_tokens > max_tokens_or_chars:
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

    # === FORMAT B: IL_COOK-style or fallback ===
    else:
        cleaned_lines = []
        last_org = None
        address_buffer = []
        in_address_block = False

        for line in raw_markdown.splitlines():
            raw = line.rstrip("\n")
            if is_page_break(raw):
                continue

            stripped = raw.strip()
            if not stripped:
                if in_address_block and address_buffer:
                    if last_org:
                        cleaned_lines.append(last_org)
                    cleaned_lines.extend(address_buffer)
                    address_buffer = []
                    in_address_block = False
                cleaned_lines.append("")
                continue

            clean_line = remove_bold(remove_header_hashes(stripped))

            if is_org_name(clean_line):
                last_org = f"**{clean_line}**"
                continue

            if is_street_address(clean_line):
                address_buffer = [clean_line]
                in_address_block = True
                continue

            if in_address_block:
                address_buffer.append(clean_line)
                if is_phone_number(clean_line):
                    if last_org:
                        cleaned_lines.append(last_org)
                    cleaned_lines.extend(address_buffer)
                    address_buffer = []
                    in_address_block = False
                continue

            cleaned_lines.append(clean_line)

        if in_address_block and address_buffer:
            if last_org:
                cleaned_lines.append(last_org)
            cleaned_lines.extend(address_buffer)

        chunks = []
        current_chunk = []
        current_length = 0

        for line in cleaned_lines:
            line_len = len(line) + 1
            is_new_org = line.startswith("**") and line.endswith("**")

            if is_new_org and current_chunk and current_length + line_len > max_tokens_or_chars:
                chunks.append("\n".join(current_chunk).strip())
                current_chunk = [line]
                current_length = line_len
            else:
                current_chunk.append(line)
                current_length += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk).strip())

        return chunks, specialty, county
