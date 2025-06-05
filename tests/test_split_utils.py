import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import split_utils

class SplitSegmentTests(unittest.TestCase):
    def test_metadata_copied(self):
        title = '"Title:news"'
        content = (
            'The local government bought a new football field. The president called africa.'
            '\n\n--tag1.jpg\nmm-tag2\nhttps://www.news.com/article.htmp\n'
            'cc-comment tag\njj-jtag\nTimestamp: 11:44pm EST\n'
        )
        original_text = title + '\n' + content
        segments = split_utils.split_segment(title, content, original_text, [0])
        self.assertEqual(len(segments), 2)
        for seg in segments:
            self.assertIn('--tag1.jpg', seg)
            self.assertIn('mm-tag2', seg)
            self.assertIn('https://www.news.com/article.htmp', seg)
            self.assertIn('cc-comment tag', seg)
            self.assertIn('jj-jtag', seg)
            self.assertIn('Timestamp: 11:44pm EST', seg)

if __name__ == '__main__':
    unittest.main()
