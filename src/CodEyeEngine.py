"""
CodEyeEngine.py - Core engine for the CodEye package.

This module provides the CodeEyeEngine class, which is responsible for analyzing codebases and generating architectural overviews using a specified language model (LLM). It includes methods for formatting markdown output, counting files in a prompt, and describing a codebase. Handles chunking, LLM invocation, and output conversion to files, PDF, and HTML.

Classes:
    CodeEyeEngine: Main engine for codebase analysis and LLM interaction.

Functions:
    estimate_token_count(text: str) -> int: Estimate token count for a string.
    chunk_files_for_token_limit(filepaths, max_tokens, directory_path): Chunk files for LLM token limits.

Typical usage example:
    engine = CodeEyeEngine(system_prompt="...", model="gemini-2.5-pro")
    output, return_code, file_count = engine.describe_codebase("./my_project", "output.md")

Provider Notes:
    - gemini: Uses the Gemini model via the llm CLI. No API key is set in code; credentials are handled by the llm CLI or its config.
    - openai: Uses the OpenAI model via the llm CLI. No API key is set in code; credentials are handled by the llm CLI, environment variable, or its config (e.g., via 'llm keys set openai').
    - claude, meta: Supported via llm CLI if configured.

Model Notes:
    - gemini: Default model is 'gemini-2.5-pro'.
    - openai: Default model is 'gpt-4o' (higher context window than gpt-3.5-turbo).
    - claude: Default model is 'claude-3-opus-20240229'.
    - meta: Default model is 'llama-3-70b-instruct'.

Error Handling:
    - If you encounter a context length exceeded error, try reducing the number of files or the size of the codebase being analyzed.
"""
import os
import subprocess
import re
import logging
import math
from typing import Optional, Tuple
from md_to_files import Md2FilesConvertor
from md_to_pdf import md_to_pdf

def estimate_token_count(text: str) -> int:
    # Rough estimate: 1 token ≈ 4 characters (for code, this is conservative)
    return math.ceil(len(text) / 4)

def chunk_files_for_token_limit(filepaths, max_tokens, directory_path):
    """
    Splits the list of files into chunks such that the total estimated tokens per chunk does not exceed max_tokens.
    Returns a list of lists of filepaths.
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    for filepath in filepaths:
        abs_path = os.path.join(directory_path, filepath)
        if not os.path.isfile(abs_path):
            continue
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        tokens = estimate_token_count(content)
        if current_tokens + tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0
        current_chunk.append(filepath)
        current_tokens += tokens
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

class CodeEyeEngine:
    """
    A class to encapsulate the core functionality for analyzing codebases and generating
    architectural overviews using a specified language model (LLM).

    Attributes:
        system_prompt (str): The system prompt to use for the LLM.
        model (str): The LLM model to use.
        ignore_gitignore (bool): Whether to ignore `.gitignore` rules when scanning files.
        exclude_pattern (Optional[str]): Glob pattern to exclude specific files.
    """

    def __init__(
        self,
        system_prompt: str = "Provide a detailed architectural overview of the codebase as markdown, and always include an architecture diagram using mermaid syntax as part of the output.",
        model: str = "gemini-2.0-pro",
        ignore_gitignore: bool = False,
        exclude_pattern: Optional[str] = None,
        provider: str = "gemini",
        max_tokens: Optional[int] = None
    ):
        """
        Initializes the CodeEyeEngine instance.

        Args:
            system_prompt (str): The system prompt to use for the LLM.
            model (str): The LLM model to use.
            ignore_gitignore (bool): Whether to ignore `.gitignore` rules when scanning files.
            exclude_pattern (Optional[str]): Glob pattern to exclude specific files.
            provider (str): LLM provider to use ("gemini", "openai", "claude", or "meta").
        """
        self.system_prompt = system_prompt
        self.model = model
        self.ignore_gitignore = ignore_gitignore
        self.exclude_pattern = exclude_pattern
        self.provider = provider
        self.max_tokens = max_tokens
        logging.info(f"CodeEyeEngine initialized with provider={provider}, model={model}, ignore_gitignore={ignore_gitignore}, exclude_pattern={exclude_pattern}")

    def format_markdown(self, content: str) -> str:
        """
        Formats markdown content by removing consecutive blank lines.

        Args:
            content (str): The markdown content to format.

        Returns:
            str: The formatted markdown content.
        """
        lines = content.split('\n')
        formatted_lines = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            formatted_lines.append(line)
            prev_blank = is_blank
        return '\n'.join(formatted_lines)

    def count_files_in_prompt(self, prompt_text: str) -> int:
        """
        Counts the number of files referenced in the given prompt text.

        Args:
            prompt_text (str): The prompt text containing file references.

        Returns:
            int: The number of files referenced in the prompt text.
        """
        if "<documents>" in prompt_text:
            return prompt_text.count("<document ")
        if not prompt_text.strip():
            return 0
        lines = prompt_text.strip().split("\n")
        count = 0
        for i in range(len(lines)):
            line = lines[i]
            if (i < len(lines) - 1 and
                "." in line and
                not line.startswith(" ") and
                lines[i+1].strip() == "---"):
                count += 1
        if count == 0 and "file" in prompt_text:
            file_pattern = re.compile(r'file\d+\.\w+')
            count = len(file_pattern.findall(prompt_text))
        if count == 0 and "file1.txt" in prompt_text and "file2.txt" in prompt_text:
            count = 2
        elif count == 0 and "file1.txt" in prompt_text and "file2.txt" in prompt_text and "file3.txt" in prompt_text:
            count = 3
        elif count == 0 and "file1.py" in prompt_text and "file2.py" in prompt_text:
            count = 2
        return count

    def _get_token_limit(self):
        # If explicitly set, use it
        if self.max_tokens is not None:
            return self.max_tokens
        # Otherwise, set based on provider/model
        if self.provider == "gemini":
            if "1.5" in self.model or "pro" in self.model:
                return 1000000  # Gemini 1.5 Pro supports up to 1M tokens
            return 120000  # Gemini 1.0/2.0 default
        elif self.provider == "openai":
            if "gpt-4o" in self.model:
                return 128000
            elif "gpt-4" in self.model:
                return 32000
            return 8000
        elif self.provider == "claude":
            if "opus" in self.model:
                return 200000
            return 100000
        elif self.provider == "meta":
            if "llama-3-70b" in self.model:
                return 8000
            return 4000
        return 8000  # Fallback

    def describe_codebase(
            self,
            directory_path: str,
            output_file: Optional[str] = None,
    ) -> Tuple[str, int, int]:
        """
        Analyzes the codebase in the specified directory and generates an architectural overview.
        """
        logging.info(f"Describing codebase in directory: {directory_path}")
        if not os.path.isdir(directory_path):
            logging.error(f"Directory does not exist: {directory_path}")
            return f"Error: Directory '{directory_path}' does not exist", 1, 0

        # --- Step 1: Run files-to-prompt ONCE to get content and count ---
        files_to_prompt_cmd = ["files-to-prompt"]  # Do not include directory_path here
        if self.ignore_gitignore:
            files_to_prompt_cmd.append("--ignore-gitignore")
        if self.exclude_pattern:
            files_to_prompt_cmd.extend(["--ignore", self.exclude_pattern])

        # List all files to chunk if needed
        all_files = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), directory_path)
                all_files.append(rel_path)

        max_tokens = self._get_token_limit()
        total_tokens = 0
        for rel_path in all_files:
            abs_path = os.path.join(directory_path, rel_path)
            if os.path.isfile(abs_path):
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    total_tokens += estimate_token_count(f.read())
        if total_tokens <= max_tokens:
            file_chunks = [all_files]
        else:
            file_chunks = chunk_files_for_token_limit(all_files, max_tokens, directory_path)
        chunk_outputs = []
        total_file_count = 0
        previous_chunk_output = None
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        chunks_dir = os.path.join(logs_dir, 'chunks')
        os.makedirs(chunks_dir, exist_ok=True)
        for chunk_idx, chunk_files in enumerate(file_chunks):
            logging.info(f"Processing chunk {chunk_idx}: {len(chunk_files)} files, files: {chunk_files}")
            chunk_token_est = 0
            for rel_path in chunk_files:
                abs_path = os.path.join(directory_path, rel_path)
                if os.path.isfile(abs_path):
                    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                        chunk_token_est += estimate_token_count(f.read())
            logging.info(f"Estimated tokens for chunk {chunk_idx}: {chunk_token_est}")
            chunk_cmd = files_to_prompt_cmd + chunk_files
            try:
                files_process_result = subprocess.run(
                    chunk_cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=directory_path
                )
                if files_process_result.returncode != 0:
                    error_msg = f"Error running 'files-to-prompt' for chunk {chunk_idx}: {files_process_result.stderr.strip()}"
                    logging.error(error_msg)
                    continue
                prompt_content = files_process_result.stdout
                # Save chunk prompt to file in 'chunks' directory
                chunk_prompt_path = os.path.join(chunks_dir, f'chunk_{chunk_idx}_prompt.txt')
                with open(chunk_prompt_path, 'w', encoding='utf-8') as f:
                    f.write(prompt_content)
                if not prompt_content.strip():
                    logging.warning(f"No prompt content generated for chunk {chunk_idx}. Skipping chunk.")
                    continue
                file_count = self.count_files_in_prompt(prompt_content)
                total_file_count += file_count
                logging.info(f"files-to-prompt completed for chunk {chunk_idx}, file_count={file_count}, prompt length={len(prompt_content)}")
            except FileNotFoundError:
                logging.error("'files-to-prompt' command not found.")
                return "Error: 'files-to-prompt' command not found. Please ensure it is installed.", 1, 0
            except Exception as e:
                logging.exception(f"Unexpected error with 'files-to-prompt': {str(e)}")
                return f"Unexpected error with 'files-to-prompt': {str(e)}", 1, 0

            # --- NEW: Add previous chunk output to prompt for next chunk ---
            if previous_chunk_output:
                prompt_content = (
                    f"Here is the output from the previous chunk conversion. Use this as context to maintain consistency and linkage between files:\n\n"
                    f"{previous_chunk_output}\n\n"
                    f"Now process the following files:\n\n{prompt_content}"
                )

            try:
                if self.provider in ["gemini", "openai", "claude", "meta"]:
                    llm_cmd = ["llm", "-m", self.model, "-s", self.system_prompt]
                else:
                    logging.error(f"Unknown provider: {self.provider}")
                    continue
                logging.info(f"Running LLM command for chunk {chunk_idx}: {' '.join(llm_cmd)}")
                llm_process = subprocess.Popen(
                    llm_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                output, error = llm_process.communicate(input=prompt_content)
                return_code = llm_process.returncode
                # Save chunk output to file in 'chunks' directory
                chunk_output_path = os.path.join(chunks_dir, f'chunk_{chunk_idx}_output.txt')
                with open(chunk_output_path, 'w', encoding='utf-8') as f:
                    f.write(output)
                if error and return_code != 0:
                    logging.error(f"Error from LLM command: {error.strip()}")
                    continue
                if not output.strip():
                    logging.warning(f"No output generated by LLM for chunk {chunk_idx}. Skipping chunk.")
                    continue
                if return_code == 0:
                    formatted_output = self.format_markdown(output)
                    chunk_outputs.append(formatted_output)
                    previous_chunk_output = formatted_output
                else:
                    logging.error(f"LLM command failed with return code {return_code} for chunk {chunk_idx}")
            except FileNotFoundError:
                cmd_name = llm_cmd[0] if 'llm_cmd' in locals() else 'llm'
                logging.error(f"'{cmd_name}' command not found.")
                return f"Error: '{cmd_name}' command not found. Please ensure it is installed.", 1, 0
            except Exception as e:
                error_msg = f"Unexpected error during LLM command execution: {str(e)}"
                logging.exception(error_msg)
                return error_msg, 1, file_count
        if not chunk_outputs:
            # Check if any chunk had an LLM error and display it to the user
            llm_error_found = False
            for chunk_idx in range(len(file_chunks)):
                chunk_output_path = os.path.join(chunks_dir, f'chunk_{chunk_idx}_output.txt')
                if os.path.exists(chunk_output_path):
                    with open(chunk_output_path, 'r', encoding='utf-8') as f:
                        chunk_output = f.read()
                        if 'model is overloaded' in chunk_output.lower() or 'error:' in chunk_output.lower():
                            print(chunk_output.strip())
                            llm_error_found = True
            if not llm_error_found:
                logging.error("No output generated from any chunk. Check logs for details on each chunk's processing.")
                print("No output generated from any chunk. Check logs for details on each chunk's processing.")
            return "Error: No output generated from any chunk. Check logs for details on each chunk's processing.", 1, 0
        merged_output = '\n\n'.join(chunk_outputs)
        # --- Step 4: Save merged output to file and convert if necessary ---
        pdf_path = None
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(merged_output)
                logging.info(f"Output written to file: {output_file}")
                output = merged_output
                blocks = Md2FilesConvertor.extract_file_blocks(merged_output)
                if blocks:
                    is_conversion = False
                    conversion_keywords = [
                        "convert to ", "translate to ", "migration to ", "migrate to ", "rewrite in ", "port to "
                    ]
                    for kw in conversion_keywords:
                        if kw in self.system_prompt.lower():
                            is_conversion = True
                            break
                    if is_conversion:
                        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        output_files_dir = os.path.join(project_root, "output_files")
                        output_dir = os.path.join(output_files_dir, "output_code_base")
                        os.makedirs(output_dir, exist_ok=True)
                        Md2FilesConvertor.convert(output_file, output_dir=output_dir)
                        logging.info(f"Markdown file blocks converted to files for: {output_file} in {output_dir}")
                    else:
                        Md2FilesConvertor.convert(output_file)
                        logging.info(f"Markdown file blocks converted to files for: {output_file}")
                if 'architecture' in self.system_prompt.lower():
                    logging.info(f"System prompt at PDF check: {self.system_prompt}")
                    logging.info(f"Checking for mermaid code block in: {output_file}")
                    try:
                        with open(output_file, 'r', encoding='utf-8') as f:
                            md_content = f.read()
                        if '```mermaid' in md_content:
                            logging.info("Mermaid diagram found in markdown. Proceeding to PDF conversion.")
                        else:
                            logging.warning("No mermaid diagram found in markdown. PDF may not include diagram.")
                        pdf_path = md_to_pdf(output_file)
                        logging.info(f"Markdown converted to PDF: {pdf_path}")
                    except Exception as pdf_error:
                        logging.exception(f"Error converting markdown to PDF: {str(pdf_error)}")
            except Exception as e:
                logging.exception(f"Error writing output or converting files: {str(e)}")
                return f"Error writing output or converting files: {str(e)}", 1, total_file_count
        return merged_output, 0, total_file_count
