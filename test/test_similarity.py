import os
import sys
import json
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from outcome_switch.outcome_comparison import OutcomeSimilarity


class SimilarityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        local_path = 'models/all-mpnet-base-v2_outcome_sim'
        remote_path = 'Mathking/all-mpnet-base-v2_outcome_sim'
        model_path = local_path if os.path.isdir(local_path) else remote_path
        cls.outcome_similarity = OutcomeSimilarity(model_path)
        with open(f'test/examples/article_outcomes.json', 'r') as f:
            article_outcomes = json.load(f)
        with open(f'test/examples/registry_outcomes.json', 'r') as f:
            registry_outcomes = json.load(f)
        cls.valid_article_outcomes = article_outcomes
        cls.valid_registry_outcomes = registry_outcomes
        cls.empty_outcomes = []

    
    def test_both_valid(self) :
        # Get similarity and test
        similarity_output = self.outcome_similarity.get_similarity(self.valid_registry_outcomes, self.valid_article_outcomes)
        self.assertEqual(len(similarity_output), 8)
    
    def test_empty_article(self) :
        # Get similarity and test
        similarity_output = self.outcome_similarity.get_similarity(self.valid_registry_outcomes, self.empty_outcomes)
        self.assertEqual(len(similarity_output), 0)
    
    def test_empty_registry(self) :
        # Get similarity and test
        similarity_output = self.outcome_similarity.get_similarity(self.empty_outcomes, self.valid_article_outcomes)
        self.assertEqual(len(similarity_output), 0)
    
    def test_both_empty(self) :
        # Get similarity and test
        similarity_output = self.outcome_similarity.get_similarity(self.empty_outcomes, self.empty_outcomes)
        self.assertEqual(len(similarity_output), 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)