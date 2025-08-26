import re

def clean_provider_markdown_grouped(raw_markdown: str, max_chars: int = 1000):
    def is_page_break(line):
        return (
            re.match(r'^(\*+)?\s*Board Certified Provider', line.strip(), re.IGNORECASE)
            or re.match(r'^\d+$', line.strip())
            or re.match(r'^-{3,}$', line.strip())
            or re.match(r'^#.*Primary Care Providers', line.strip(), re.IGNORECASE)
            or re.match(r'^## Page \d+', line.strip(), re.IGNORECASE)
        )

    def is_org_name(line):
        org_keywords = r'(Center|Clinic|Health|Hospital|Medical|Access|Sinai|Practice|Group|SC|Ltd|Midwest|Inc)'
        return bool(re.search(org_keywords, line.strip(), re.IGNORECASE))

    def is_bolded(line):
        return line.strip().startswith("**") and line.strip().endswith("**")

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
    county = county_match.group(1).title().strip() if county_match else None

    specialty_match = re.search(r'####\s*(.+)', raw_markdown)
    specialty = specialty_match.group(1).strip() if specialty_match else None

    # --- Cleaning logic ---
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
            continue  # delay insertion

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

    # --- Chunking logic ---
    chunks = []
    current_chunk = []
    current_length = 0

    for line in cleaned_lines:
        line_len = len(line) + 1
        is_new_org = line.startswith("**") and line.endswith("**")

        if is_new_org and current_chunk and current_length + line_len > max_chars:
            chunks.append("\n".join(current_chunk).strip())
            current_chunk = [line]
            current_length = line_len
        else:
            current_chunk.append(line)
            current_length += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk).strip())

    return chunks, specialty, county
