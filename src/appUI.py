"""
Streamlit UI for CodEye Engine.

Features:
- Upload a zipped code directory or specify a server-side path.
- Configure LLM provider, model, and additional options.
- Enter a system prompt for code analysis or conversion.
- Run analysis/conversion via CLI and display/download results.
- Reset and help actions available in the UI.

Author: [Your Name or Team]
"""

import streamlit as st
import tempfile
import os
import zipfile
import subprocess
import shutil
from pathlib import Path

# Show logo above directory input in sidebar
logo_path = Path(__file__).resolve().parents[1] / 'logo.jpg'
if logo_path.exists():
    st.sidebar.image(str(logo_path), width=240, caption="CodEye Engine")
else:
    st.sidebar.warning("Logo not found: logo.jpg")

# Sidebar for directory input
st.sidebar.header("Directory Input")
uploaded_file = st.sidebar.file_uploader("Upload a zipped directory", type=["zip"])
directory_path = st.sidebar.text_input("Or enter directory path (server-side)", "")

st.title("AEye CodEye")

# System prompt textbox directly below title (no header)
system_prompt = st.text_area("System Prompt", value="convert to python", placeholder="Enter system prompt...", label_visibility="collapsed")

# Analyze/Convert button moved directly below system prompt
analyze_clicked = st.button("Analyze/Convert")

# Download button area - appears here after analysis is complete
download_placeholder = st.empty()

# Configuration options that need to be defined before the analyze button
# Provider and Model selection
st.header("Model Configuration")
provider_model_map = {
    "gemini": ["gemini-2.5-pro"],
    "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
    "claude": ["claude-3-opus", "claude-3-sonnet"],
    "meta": ["llama-3-70b", "llama-2-13b"]
}
provider = st.selectbox("Select Provider", list(provider_model_map.keys()), index=0)
model = st.selectbox("Select Model", provider_model_map[provider], index=0)

# Checkboxes
st.header("Options")
ignore_gitignore = st.checkbox("Ignore .gitignore")
quiet_mode = st.checkbox("Quiet Mode")

# Text inputs
st.header("Additional Parameters")
exclude_pattern = st.text_input("Exclude Pattern (e.g., '*.pl backups')")
output_file = st.text_input("Output File Name (optional, .md)")


def run_cli(directory, system_prompt, model, provider, output, ignore_gitignore, exclude, quiet):
    """
    Run the CLI tool with the specified parameters.

    Args:
        directory (str): Path to the codebase directory.
        system_prompt (str): System prompt for the LLM.
        model (str): Model name.
        provider (str): Provider name.
        output (str): Output file name.
        ignore_gitignore (bool): Whether to ignore .gitignore.
        exclude (str): Exclude pattern.
        quiet (bool): Quiet mode.

    Returns:
        tuple: (stdout, stderr) from the CLI process.
    """
    cli_path = os.path.join(os.path.dirname(__file__), "cli.py")
    args = ["python", cli_path, directory]
    if system_prompt:
        args += ["-s", system_prompt]
    if model:
        args += ["-m", model]
    if provider:
        args += ["--provider", provider]
    if output:
        args += ["-o", output]
    if ignore_gitignore:
        args += ["--ignore-gitignore"]
    if exclude:
        args += ["--exclude", exclude]
    if quiet:
        args += ["--quiet"]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout, result.stderr

# Results pane below the button
if analyze_clicked:
    temp_dir = None
    directory = None
    # Handle uploaded zip
    if uploaded_file:
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
        # Use the first directory inside temp_dir as the codebase root
        extracted_items = [os.path.join(temp_dir, name) for name in os.listdir(temp_dir)]
        dirs = [item for item in extracted_items if os.path.isdir(item)]
        directory = dirs[0] if dirs else temp_dir
    elif directory_path:
        directory = directory_path
    else:
        st.error("Please upload a zipped directory or enter a directory path.")
        st.stop()

    # Show magic wand spinner while processing with dynamic message
    prompt_text = system_prompt.strip() if system_prompt else ""

    if not prompt_text:
        spinner_message = '🪄 Analyzing... Please wait!'
    elif 'convert' in prompt_text.lower():
        spinner_message = '🪄 Analyzing and Converting... Please wait!'
    else:
        spinner_message = '🪄 Analyzing... Please wait!'

    with st.spinner(spinner_message):
        output, error = run_cli(
            directory,
            system_prompt,
            model,
            provider,
            output_file,
            ignore_gitignore,
            exclude_pattern,
            quiet_mode
        )

    if error:
        st.error(f"Error: {error}")
    else:
        # Show download button in the placeholder area (below system prompt)
        with download_placeholder.container():
            # Enhanced download functionality
            if output_file and output_file.strip():
                # Try to find the output file in the output_files directory
                output_dir = os.path.join(os.path.dirname(__file__), "output_files")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, os.path.basename(output_file))

                if os.path.exists(output_path):
                    with open(output_path, "rb") as f:
                        st.download_button(
                            "📥 Download Results",
                            f,
                            file_name=output_file,
                            mime="text/markdown",
                            key="download_results"
                        )
                else:
                    # If file doesn't exist, create it with the output content
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(output)
                    with open(output_path, "rb") as f:
                        st.download_button(
                            "📥 Download Results",
                            f,
                            file_name=output_file,
                            mime="text/markdown",
                            key="download_results"
                        )
            else:
                # If no output file specified, offer to download the results as a default file
                default_filename = "analysis_results.md"
                st.download_button(
                    "📥 Download Results",
                    output,
                    file_name=default_filename,
                    mime="text/markdown",
                    key="download_results_default"
                )

        # Display results below the configuration section
        st.markdown("### Analysis Results")
        st.markdown(output)

    # Clean up temp dir
    if temp_dir:
        shutil.rmtree(temp_dir)

# Action buttons
col1, col2 = st.columns(2)
reset_clicked = col1.button("Reset")
help_clicked = col2.button("Help")

if help_clicked:
    st.info("""
    **CLI Help:**
    - `directory`: Path to the codebase directory (required)
    - `--system-prompt`: Custom system prompt for the model (default: "convert to python")
    - `--model`: LLM model to use (default: based on provider, e.g., gemini-2.5-pro)
    - `--provider`: LLM provider (default: gemini)
    - `--output`: Output markdown file path (optional)
    - `--ignore-gitignore`: Ignore files listed in .gitignore
    - `--exclude`: Glob pattern to exclude files (e.g., '*.pl backups')
    - `--quiet`: Suppress verbose output

    **Model Notes:**
    - `gemini-2.5-pro`: Default Gemini model
    - `gpt-4o`: Optimized OpenAI model
    - `claude-3-opus`: High performance for reasoning tasks
    - `llama-3-70b`: Meta's large language model
    """)

if reset_clicked:
    st.rerun()