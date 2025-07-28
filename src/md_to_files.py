"""
md_to_files.py - Markdown to Files Converter for CodEye

This module provides the Md2FilesConvertor class, which extracts code/file blocks from a markdown file and writes them as individual files to a specified output directory. Used for codebase conversion and reconstruction from markdown LLM output.

Classes:
    Md2FilesConvertor: Static methods for extracting and writing code blocks from markdown to files.

Typical usage example:
    Md2FilesConvertor.convert('output.md', output_dir='output_files')
"""

import os
import re
import sys

class Md2FilesConvertor:
    @staticmethod
    def extract_file_blocks(md_content):
        """
        Extracts file blocks from the markdown content.
        Returns a list of tuples: (filepath, code, language)
        Only extracts blocks that start with a valid language and a valid file path comment.
        Ignores blocks where the file path is not a valid file path (e.g., markdown headings).
        """
        code_block_pattern = re.compile(
            r"```(\w+)?\s*\n#\s*([^\n]+)\n(.*?)```",
            re.DOTALL
        )
        blocks = []
        for match in code_block_pattern.finditer(md_content):
            lang = match.group(1) or ""
            filepath = match.group(2).strip()
            code = match.group(3)
            # Only allow filepaths that look like real files (must have an extension, no markdown heading)
            if re.match(r"^[\w\-./]+\.[\w\d]+$", filepath):
                blocks.append((filepath, code, lang))
        return blocks

    @staticmethod
    def write_file(filepath, code):
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code.lstrip("\n"))

    @staticmethod
    def convert(md_path, output_dir=None):
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        blocks = Md2FilesConvertor.extract_file_blocks(md_content)
        if not blocks:
            print("No file blocks found.")
            return
        # Default output_dir to 'output_files' in the script's parent directory if not provided
        if output_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, "output_files")
        for filepath, code, lang in blocks:
            # Always write inside output_dir, preserving subdirectories, but prevent escaping
            safe_filepath = os.path.normpath(filepath).replace("..", "")
            abs_path = os.path.join(output_dir, safe_filepath)
            Md2FilesConvertor.write_file(abs_path, code)
            print(f"Wrote: {abs_path}")
