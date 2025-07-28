import unittest
import os
from src.md_to_files import Md2FilesConvertor

class TestMd2FilesConvertor(unittest.TestCase):
    def setUp(self):
        self.test_md = """
```python
# test_dir/test_file.py
print('hello world')
```
```txt
# test_dir/readme.txt
This is a test.
```
"""
        self.test_md_path = "test_input.md"
        with open(self.test_md_path, "w", encoding="utf-8") as f:
            f.write(self.test_md)
        self.output_dir = "test_output_files"
        if os.path.exists(self.output_dir):
            import shutil
            shutil.rmtree(self.output_dir)

    def tearDown(self):
        if os.path.exists(self.test_md_path):
            os.remove(self.test_md_path)
        if os.path.exists(self.output_dir):
            import shutil
            shutil.rmtree(self.output_dir)

    def test_extract_file_blocks(self):
        with open(self.test_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = Md2FilesConvertor.extract_file_blocks(content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0][0], "test_dir/test_file.py")
        self.assertIn("hello world", blocks[0][1])

    def test_convert_creates_files(self):
        Md2FilesConvertor.convert(self.test_md_path, output_dir=self.output_dir)
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "test_dir/test_file.py")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "test_dir/readme.txt")))

if __name__ == "__main__":
    unittest.main()

