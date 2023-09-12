import sys
import json
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from outcome_switch.registry import CTGOVExtractor
from outcome_switch.utils import convert_registry_outcomes


class CTGOVExtractorTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.extractor = CTGOVExtractor()
    
    def test_nct_detection(self):
        with open('test/examples/raw_and_parsed.json', 'r') as f:
            xml_full_text = json.load(f)["article_xml_string"]
        nct_id = self.extractor.find_nct_id(xml_full_text)
        self.assertEqual(nct_id, 'NCT01623843') 

    def test_get_info(self):
        nct_id = 'NCT01623843'
        registry_outcomes = self.extractor.get_all_infos(nct_id)
        # self.assertEqual(len(registry_outcomes["outcomes"]) , 13)
        # self.assertEqual(len(registry_outcomes) , 15)
        with open('test/examples/registry_infos.json', 'w') as f:
            json.dump(registry_outcomes, f, indent=4)


if __name__ == '__main__':
    unittest.main(verbosity=2)