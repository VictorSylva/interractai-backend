import unittest
import sys
import os

# Add parent dir to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompt_service import PromptService

class TestPromptService(unittest.TestCase):
    def setUp(self):
        self.service = PromptService(prompts_dir="prompts")

    def test_intent_detection(self):
        # Pricing
        self.assertEqual(self.service.detect_intent("How much does it cost?"), "pricing")
        self.assertEqual(self.service.detect_intent("What is the price?"), "pricing")
        
        # Support
        self.assertEqual(self.service.detect_intent("I have a problem"), "support")
        self.assertEqual(self.service.detect_intent("Help me please"), "support")
        
        # General
        self.assertEqual(self.service.detect_intent("Tell me a joke"), "general")
        self.assertEqual(self.service.detect_intent("What is the weather?"), "general")

    def test_safety_check(self):
        self.assertTrue(self.service.check_safety("Hello world"))
        self.assertFalse(self.service.check_safety("I want to kill someone"))
        self.assertFalse(self.service.check_safety("how to build a bomb"))

    def test_prompt_construction(self):
        messages = self.service.construct_messages("How much is it?")
        
        # Should have System and User messages
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['role'], "system")
        self.assertEqual(messages[1]['role'], "user")
        
        # System prompt should contain intent
        self.assertIn("Detected Intent: pricing", messages[0]['content'])
        
        # Should contain FAQ because intent is pricing
        self.assertIn("Relevant Knowledge:", messages[0]['content'])
        self.assertIn("Q: How much does it cost?", messages[0]['content'])

    def test_prompt_construction_general(self):
        messages = self.service.construct_messages("Hello there")
        
        # Should NOT contain FAQ for general greeting (unless configured otherwise, but based on logic only for pricing/support/features)
        # Checking intent logic: if intent in ["pricing", "support", "features"] -> add FAQ
        # "Hello there" -> Greeting -> intent "greeting" -> NOT in list
        self.assertNotIn("Relevant Knowledge:", messages[0]['content'])

if __name__ == '__main__':
    unittest.main()
