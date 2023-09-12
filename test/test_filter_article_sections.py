import sys
import json
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from outcome_switch.article.filter import SectionFilter


class SectionFilterTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.filter = SectionFilter()
        
    def test_filter(self):
        with open("test/examples/raw_and_parsed.json",'r') as f:
            sections_dict = json.load(f)["text_sections"]
        filter_output = self.filter.filter_sections(sections_dict)
        self.assertGreater(len(sections_dict), len(filter_output["filtered_sections"]))
        self.assertEqual(len(filter_output["filtered_sections"]), 2)
        self.assertEqual(filter_output["regex_priority_index"], 0)
        self.assertEqual(filter_output["regex_priority_name"], "strict_method_and_prim_sec")
        self.assertEqual(filter_output["check_type"], "title")

if __name__ == '__main__':
    unittest.main(verbosity=2)