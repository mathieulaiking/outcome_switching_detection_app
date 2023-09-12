import sys
import json
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from outcome_switch.article.download import IDDownloader

class IDDownloaderTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.downloader = IDDownloader(logging_mode='none')

    def test_pmcid_fetch(self):
        valid_pmcid = ['PMC6206648']
        valid_response = self.downloader.fetch_xml(valid_pmcid)[0]
        self.assertTrue(valid_response)
    
    def test_invalid_pmcid(self):
        invalid_pmcid = ['PMC0000000']
        test_xml = self.downloader.fetch_xml(invalid_pmcid)
        self.assertEqual(test_xml, [])
    
    def test_empty_download(self):
        empty_pmcid = []
        with self.assertRaises(ValueError):
            self.downloader.fetch_xml(empty_pmcid)


if __name__ == '__main__':
    unittest.main(verbosity=2)