import os
import sys
import json
from pathlib import Path
from parse import PDFExtractor
import pandas as pd

import Extractor_CA_LA
import cleanmd_ca_la
import Extractor_IL_COOK
import cleanmd_il_cook
from config import OUTPUT_PATH,PDF_PATH,LLAMA_API_KEY,PROMPT_IL_COOK,PROMPT_CA_LA

def get_cleaner_and_extractor(pdf_name: str):
    if "ca_la" in pdf_name.lower():
        return cleanmd_ca_la.clean_provider_markdown, Extractor_CA_LA.extract_providers
    elif "il_cook" in pdf_name.lower():
        return cleanmd_il_cook.clean_provider_markdown_grouped, Extractor_IL_COOK.extract_providers
    else:
        raise ValueError("Unable to determine cleaner/extractor from filename.")


def run_pipeline(pdf_path: str, prompt_path: str, api_key: str, output_dir: str):
    pdf_name = Path(pdf_path).stem
    raw_md_path = Path(output_dir) / f"{pdf_name}_raw.md"
    cleaned_md_path = Path(output_dir) / f"cleaned_{pdf_name}.md"
    json_output_path = Path(output_dir) / f"extracted_providers_{pdf_name}.json"

    print(f"\n🔍 Running pipeline for: {pdf_name}")
    print(f"📄 Reading prompt from: {prompt_path}")

    # Step 1: Read prompt
    with open(prompt_path, "r", encoding="utf-8") as f:
        user_prompt = f.read()

    # Step 2: Extract using LlamaParse
    print("🧠 Extracting text with LlamaParse...")
    extractor = PDFExtractor(pdf_path=pdf_path, llama_api_key=api_key)
    extractor.user_prompt = user_prompt
    pages = extractor.extract(parser_type="llama_parser")

    if not pages:
        print("❌ No pages extracted.")
        return

    # Step 3: Save raw markdown
    markdown_content = "\n".join(
        f"## Page {p.page_number}\n{p.content.strip()}\n---\n" for p in pages
    )
    with open(raw_md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"✅ Raw markdown saved at: {raw_md_path}")
    return 
    # Step 4: Get cleaner and extractor
    clean_func, extract_func = get_cleaner_and_extractor(pdf_name)

    # Step 5: Clean markdown
    print("🧹 Cleaning markdown content...")
    if "ca_la" in pdf_name.lower():
        chunks, county, specialty = clean_func(markdown_content)
    elif "il_cook" in pdf_name.lower():
        chunks, specialty, county = clean_func(markdown_content)
    else:
        raise ValueError("Unsupported PDF type for cleaning.")

    print(f"🧩 Markdown split into {len(chunks)} chunks")
    print(f"📍 County: {county}, 🏥 Specialty: {specialty}")
    chunk_dir = Path(output_dir) / f"{pdf_name}_chunks"
    chunk_dir.mkdir(exist_ok=True)

    for i, chunk in enumerate(chunks, 1):
        chunk_file = chunk_dir / f"{pdf_name}_chunk_{i}.md"
        with open(chunk_file, "w", encoding="utf-8") as cf:
            cf.write(chunk)

    print(f"🗂️ Saved {len(chunks)} chunks to: {chunk_dir}")

    all_providers = []
    for i, chunk in enumerate(chunks):
        print(f"🔎 Extracting providers from chunk {i+1}...")
        extracted_data = extract_func(
            current_page_content=chunk,
            previous_page_content=None,
            specialty=specialty,
            county=county,
        )
        all_providers.extend(extracted_data.providers)

    # Step 6: Save cleaned markdown
    cleaned_output = "\n---\n".join(chunks)
    with open(cleaned_md_path, "w", encoding="utf-8") as f:
        f.write(cleaned_output)
    print(f"✅ Cleaned markdown saved at: {cleaned_md_path}")

    # Step 7: Post-process and save
    valid_providers = []
    for p in all_providers:
        try:
            if not (p.full_name or p.practice_name):
                continue
            if not p.county:
                p.county = county
            if not p.specialty:
                p.specialty = specialty
            valid_providers.append(p)
        except Exception as e:
            print("❌ Error processing provider:", p)
            print("Error:", e)
            exit()

    print(f"🧑‍⚕️ Total valid providers extracted: {len(valid_providers)}")

    if valid_providers:
        try:
            df = pd.DataFrame([p.model_dump() for p in valid_providers])  # Fix for Pydantic 2.x
            csv_output_path = Path(output_dir) / f"extracted_providers_{pdf_name}.csv"
            df.to_csv(csv_output_path, index=False)
            print(f"📊 CSV saved at: {csv_output_path}")
        except Exception as e:
            print("❌ Error saving CSV:", e)
    else:
        print("⚠️ No provider data found to save.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run provider extraction pipeline using LlamaParse.")
    parser.add_argument("--pdf_path", type=str, default=None, help="Path to the input PDF file.")
    parser.add_argument("--output_dir", type=str, default=None, help="Directory to store outputs.")
    parser.add_argument("--api_key", type=str, default=None, help="LlamaParse API key.")

    args = parser.parse_args()

    # Handle inputs and defaults
    pdf_path = args.pdf_path
    output_dir = args.output_dir
    api_key = args.api_key or LLAMA_API_KEY

    # Validate pdf_path and output_dir based on your rules
    if pdf_path is None and output_dir is None:
        # Use both defaults
        pdf_path = PDF_PATH
        output_dir = OUTPUT_PATH
        # print(f"Using default PDF path: {pdf_path}")
        # print(f"Using default output directory: {output_dir}")
    elif pdf_path is not None and output_dir is None:
        # Use provided pdf_path and default output_dir
        output_dir = OUTPUT_PATH
        # print(f"Using provided PDF path: {pdf_path}")
        # print(f"Using default output directory: {output_dir}")
    elif pdf_path is None and output_dir is not None:
        print("Error: Output directory provided but no PDF input path specified.")
        sys.exit(1)
    

    # Check if PDF file exists
    if not Path(pdf_path).is_file():
        print(f"Error: PDF file not found at '{pdf_path}'.")
        sys.exit(1)

    # Check if output directory exists or create it
    #output_dir_path = Path(output_dir)
    #output_dir_path.mkdir(parents=True, exist_ok=True)

    # Auto-select prompt based on PDF filename
    pdf_name = Path(pdf_path).stem.lower()
    prompt_map = {
    "il_cook": PROMPT_IL_COOK,
    "ca_la": PROMPT_CA_LA,
}
    selected_prompt = None
    for key, prompt_path in prompt_map.items():
        if key in pdf_name:
            selected_prompt = prompt_path
            # print(f"Auto-selected prompt for '{key}': {selected_prompt}")
            break

    if not selected_prompt:
        # print(f"Could not determine prompt for PDF: {pdf_name}. Please update prompt_map.")
        sys.exit(1)

    folder_path= r"C:\Users\Renuka Kolusu\Downloads\renuka_task\renuka_task/"
    for pdf in os.listdir(folder_path):
        pdf_path= folder_path + pdf
        # Run extraction pipeline
        run_pipeline(
            pdf_path=pdf_path,
            prompt_path=selected_prompt,
            api_key=api_key,
            output_dir=output_dir
        )
