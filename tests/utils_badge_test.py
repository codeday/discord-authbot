import unittest

from utils import badge


class test_get_badges(unittest.TestCase):
    def test_get(self):
        badges = badge.get_badges()
        self.assertIsInstance(badges, list)
        for b in badges:
            self.assertIsInstance(b, dict)
            self.assertIn('id', b)
            self.assertIn('name', b)
            self.assertIn('description', b)
            self.assertIn('emoji', b)


if __name__ == '__main__':
    unittest.main()
