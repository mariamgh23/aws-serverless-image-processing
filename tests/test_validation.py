import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "src" / "lambda_function.py"
spec = importlib.util.spec_from_file_location("lambda_function", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ValidationTests(unittest.TestCase):
    def test_accepts_incoming_image_key(self):
        self.assertTrue(module.is_allowed_source_key("incoming/product-01.png"))

    def test_rejects_key_outside_incoming_prefix(self):
        self.assertFalse(module.is_allowed_source_key("thumbnails/product-01.png"))

    def test_rejects_folder_key(self):
        self.assertFalse(module.is_allowed_source_key("incoming/"))


if __name__ == "__main__":
    unittest.main()
