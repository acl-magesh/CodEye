import unittest
import os
import subprocess
import sys

class TestCli(unittest.TestCase):
    def setUp(self):
        self.cli_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'cli.py')
        self.test_dir = os.path.join(os.path.dirname(__file__), '..')
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', 'output_files')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, 'test_cli_output.md')
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_cli_runs_and_creates_output(self):
        # Use a minimal directory (the src dir itself) for a quick test
        args = [sys.executable, self.cli_path, self.test_dir, '-o', self.output_file, '--quiet']
        result = subprocess.run(args, capture_output=True, text=True)
        if not os.path.exists(self.output_file):
            print('STDOUT:', result.stdout)
            print('STDERR:', result.stderr)
        self.assertIn('Output written to', result.stdout + result.stderr)
        self.assertTrue(os.path.exists(self.output_file))
        # Check that the output file is not empty
        with open(self.output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertTrue(len(content.strip()) > 0)

if __name__ == "__main__":
    unittest.main()
