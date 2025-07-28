# CodEye: AI-Powered Codebase Analysis & Conversion Tool

## Project Overview and Purpose
CodEye is an advanced tool designed to analyze, document, and convert codebases using state-of-the-art Large Language Models (LLMs) such as Gemini, OpenAI, Claude, and Meta. It provides architectural overviews, generates diagrams, and can migrate codebases between languages, making it ideal for software architects, developers, and teams seeking automated insights or codebase modernization.

## Features and Architecture Summary
- **Multi-Provider LLM Support:** Integrates with Gemini, OpenAI, Claude, and Meta models.
- **Codebase Analysis:** Generates detailed architectural overviews, including mermaid diagrams.
- **Automated Code Conversion:** Converts entire codebases to a target language with best-practice supporting files.
- **Streamlit UI:** User-friendly web interface for uploading code, configuring models, and viewing results.
- **CLI Tool:** Command-line interface for batch processing and automation.
- **Markdown, PDF, and HTML Output:** Outputs results in markdown, and can generate PDF/HTML with rendered diagrams.
- **File Extraction:** Reconstructs codebases from markdown LLM output.
- **Logging and Chunking:** Handles large codebases by chunking and logs all operations for traceability.

## Setup and Installation Instructions
### Prerequisites
- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- [Playwright](https://playwright.dev/python/) (for PDF/HTML export)
- LLM provider credentials (e.g., OpenAI API key, Gemini setup, etc.)

### Installation
1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd CodEye
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   playwright install
   ```
3. **(Optional) Configure LLM credentials:**
   - For OpenAI: `llm keys set openai` or set `OPENAI_API_KEY`.
   - For Gemini: Follow [llm CLI Gemini setup](https://github.com/simonw/llm).

## How to Run the Application
### Command-Line Interface (CLI)
Run analysis or conversion from the command line:
```sh
python src/cli.py <directory> [options]
```
**Example:**
```sh
python src/cli.py ../input_code_base/starman -o starman_architecture.md
```

### Streamlit Web UI
Launch the web interface:
```sh
streamlit run src/appUI.py
```

## How to Run Tests
If tests are available, run them using:
```sh
python -m unittest discover -s tests
```
Or with pytest (if used):
```sh
pytest tests/
```

## Usage Examples
- **Analyze a codebase:**
  ```sh
  python src/cli.py ../input_code_base/starman -o output.md
  ```
- **Convert a codebase to Python:**
  ```sh
  python src/cli.py ../input_code_base/starman "convert to python" -o python_output.md
  ```

## Contribution Guidelines
- Fork the repository and create a feature branch.
- Write clear commit messages and document your code.
- Ensure all tests pass before submitting a pull request.
- For major changes, open an issue first to discuss your proposal.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

