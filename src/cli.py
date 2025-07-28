"""
cli.py - Command-line interface for the CodEye package.

This script provides a command-line interface for analyzing codebases and generating architectural overviews using the CodeEyeEngine class. It allows users to specify various options such as the directory to analyze, the system prompt, the model to use, and output file settings.

Usage:
    python cli.py <directory> [options]

Arguments:
    directory (str): The directory to analyze.

Options:
    -s, --system-prompt (str): The system prompt to use for the LLM (default: detailed architecture overview prompt).
    -m, --model (str): The LLM model to use (default: based on provider).
    --provider (str): The LLM provider to use (default: gemini; options: gemini, openai, claude, meta).
    -o, --output (str): The path to the output markdown file.
    --ignore-gitignore: Ignore .gitignore rules when scanning files.
    --exclude (str): Glob pattern to exclude specific files (e.g., '*.test.ts').
    --quiet: Suppress file count information in the output.

Returns:
    Writes the architectural overview to the specified output file or stdout.
    Exits with code 0 on success, 1 on error.

Example:
    python cli.py ../input_code_base/starman -o starman_architecture.md

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

# Library imports
import argparse
import os
import sys
import logging
from CodEyeEngine import CodeEyeEngine

def main():
    # Setup logging
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(logs_dir, 'codeye.log'),
        filemode='a',
        format='%(asctime)s %(levelname)s: %(message)s',
        level=logging.INFO
    )
    logging.info('Starting CLI process')

    """
    Entry point for the command-line interface.

    This function parses command-line arguments, initializes the CodeEyeEngine instance,
    and performs the codebase analysis. It handles output formatting, file count display,
    and error handling.

    Command-line arguments:
        directory (str): The directory to analyze.
        -s, --system-prompt (str): The system prompt to use for the LLM (default: "architectural overview as markdown").
        -m, --model (str): The LLM model to use (default: "gemini-2.5-flash").
        --provider (str): The LLM provider to use (default: "gemini").
        -o, --output (str): The path to the output markdown file.
        --ignore-gitignore (bool): Whether to ignore `.gitignore` rules when scanning files.
        --exclude (str): Glob pattern to exclude specific files (e.g., '*.test.ts').
        --quiet (bool): Suppress file count information in the output.

    Raises:
        SystemExit: Exits the program with the appropriate return code.
    """
    parser = argparse.ArgumentParser(
        description="Generate architectural overviews of codebases using Gemini AI"
    )
    parser.add_argument(
        "directory",
        help="Directory to analyze"
    )
    parser.add_argument(
        "-s", "--system-prompt",
        default="Provide a detailed architectural overview of the codebase as markdown, and always include an architecture diagram using mermaid syntax as part of the output.",
        help="System prompt to use for the LLM"
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="LLM model to use"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "claude", "meta"],
        default="gemini",
        help="LLM provider to use (default: gemini; options: gemini, openai, claude, meta)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Write output to specified markdown file instead of stdout"
    )
    parser.add_argument(
        "--ignore-gitignore",
        action="store_true",
        help="Ignore .gitignore rules when scanning files (by default, .gitignore rules are respected)"
    )
    parser.add_argument(
        "--exclude",
        help="Exclude files matching this glob pattern (e.g., '*.test.ts')"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Don't display file count information"
    )

    # Parse only the known arguments, ignoring any extras
    args, unknown = parser.parse_known_args()

    # Set default model based on provider if not specified
    if args.model is None:
        if args.provider == "gemini":
            args.model = "gemini-2.5-pro"
        elif args.provider == "openai":
            args.model = "gpt-4o"
        elif args.provider == "claude":
            args.model = "claude-3-opus-20240229"
        elif args.provider == "meta":
            args.model = "llama-3-70b-instruct"

    # Handle unknown arguments and set the system prompt if not explicitly provided
    if unknown and "-s" not in sys.argv and "--system-prompt" not in sys.argv:
        args.system_prompt = " ".join(unknown)

    # Ensure the output file has a .md extension if specified
    if args.output:
        output_dir = os.path.join(os.path.dirname(__file__), 'output_files')
        os.makedirs(output_dir, exist_ok=True)
        base_output = os.path.basename(args.output)
        if not base_output.lower().endswith('.md'):
            base_output = base_output + '.md'
        args.output = os.path.join(output_dir, base_output)


    # Detect code conversion intent in the system prompt BEFORE initializing the engine
    conversion_keywords = [
        "convert to ", "translate to ", "migration to ", "migrate to ", "rewrite in ", "port to "
    ]
    lower_prompt = args.system_prompt.lower()
    target_language = None
    for kw in conversion_keywords:
        if kw in lower_prompt:
            # Extract the language after the keyword
            idx = lower_prompt.find(kw) + len(kw)
            # Take the next word as the language (strip punctuation)
            rest = lower_prompt[idx:].strip()
            if rest:
                # Only take the first word (language), ignore extra words
                target_language = rest.split()[0].strip('.,:;!')
            break
    if target_language:
        args.system_prompt = (
            f"Convert the codebase to {target_language} as requested. "
            f"Output the result as markdown file blocks, where each code block starts with the language, followed by a comment line with the file path, "
            f"and then the code content. For example: ```{target_language}\n# path/to/file.{target_language}\n...code...```. "
            f"Ensure every file to be created or converted is represented as a separate code block in this format. "
            f"Do not include any prose, explanation, or review comments—only the file blocks. "
            f"For files like README, requirements.txt, setup.py, etc., generate them according to best practices for {target_language}. "
            f"The README.md file must be comprehensive and include: "
            f"- Project overview and purpose\n"
            f"- Features and architecture summary\n"
            f"- Setup and installation instructions (including prerequisites)\n"
            f"- How to install dependencies\n"
            f"- How to run the application (with example commands)\n"
            f"- How to run tests (if applicable)\n"
            f"- Usage examples\n"
            f"- Contribution guidelines (if appropriate)\n"
            f"- License section\n"
            f"All supporting files should be adapted for the new language and ecosystem."
        )
    elif any(kw in lower_prompt for kw in conversion_keywords):
        args.system_prompt = (
            "Convert the codebase to the target language as requested. "
            "Output the result as markdown file blocks, where each code block starts with the language, followed by a comment line with the file path, "
            "and then the code content. For example: ```python\n# path/to/file.py\n...code...```. "
            "Ensure every file to be created or converted is represented as a separate code block in this format. "
            "Do not include any prose, explanation, or review comments—only the file blocks. "
            "For files like README, requirements.txt, setup.py, etc., generate them according to best practices for the target language. "
            "The README.md file must be comprehensive and include: "
            "- Project overview and purpose\n"
            "- Features and architecture summary\n"
            "- Setup and installation instructions (including prerequisites)\n"
            "- How to install dependencies\n"
            "- How to run the application (with example commands)\n"
            "- How to run tests (if applicable)\n"
            "- Usage examples\n"
            "- Contribution guidelines (if appropriate)\n"
            "- License section\n"
            "All supporting files should be adapted for the new language and ecosystem."
        )

    try:
        # Initialize the CodeEyeEngine instance
        cee = CodeEyeEngine(
            system_prompt=args.system_prompt,
            model=args.model,
            ignore_gitignore=args.ignore_gitignore,
            exclude_pattern=args.exclude,
            provider=args.provider
        )
        logging.info(f'Initialized CodeEyeEngine with provider={args.provider}, model={args.model}')
        # Run the core function to describe the codebase
        output, return_code, file_count = cee.describe_codebase(
            args.directory,
            args.output
        )
        logging.info(f'Codebase described: return_code={return_code}, file_count={file_count}')
    except Exception as e:
        logging.exception(f'Exception occurred during CLI execution: {e}')
        print(f"An error occurred: {e}")
        sys.exit(1)

    # Display file count information unless quiet mode is enabled
    if not args.quiet and file_count > 0 and return_code == 0:
        logging.info(f"Analyzed {file_count} file{'s' if file_count != 1 else ''} from {os.path.abspath(args.directory)}")
        if args.ignore_gitignore:
            logging.info("Note: .gitignore rules were ignored")
        if args.exclude:
            logging.info(f"Excluded files matching: {args.exclude}")
        logging.info("")  # Add empty line for better readability

    # Handle output based on return code and output file
    if not args.output:
        # No output file specified, just print to console
        print(output)
    elif return_code == 0:
        # Only show success message if there was no error
        output_path = os.path.abspath(args.output)
        print(f"Output written to: {output_path}")
    else:
        # If there was an error, just print the error message
        print(output)

    # Exit the program with the appropriate return code
    sys.exit(return_code)


if __name__ == "__main__":
    main()