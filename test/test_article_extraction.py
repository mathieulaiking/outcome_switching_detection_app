import os
import sys
import json
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from outcome_switch.article.extraction import ChunkTokenClassificationPipeline
from outcome_switch.utils import filter_outcomes

class OutcomeExtractionTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        if os.path.isdir('models/PubMedBERT-base-uncased-abstract-finetuned-outcomes-ner'):
            model_path = 'models/PubMedBERT-base-uncased-abstract-finetuned-outcomes-ner'
        else:
            model_path = 'Mathking/PubMedBERT-base-uncased-abstract-finetuned-outcomes-ner'
        cls.pipeline = ChunkTokenClassificationPipeline(model_path)

        
    def test_valid_extraction_and_outcome_filtering(self):
        with open('test/examples/filtered_sections.json', 'r') as f:
            sections_dict = json.load(f)
        sections_text = ""
        for title, section_content in sections_dict.items():
            sections_text += ' \n '.join([title] + section_content)
            sections_text += '\n\n'
        entities = self.pipeline(sections_text)
        self.assertEqual(entities[1]["entity_group"], "Prim")
        entities = filter_outcomes(entities)
        self.assertEqual(len(entities), 10) # the model predicts some wrong secondary outcomes
    
    

if __name__ == '__main__':
    unittest.main(verbosity=2)