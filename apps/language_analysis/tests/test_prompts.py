from django.test import SimpleTestCase

from apps.language_analysis.prompts.linguistic_analysis import SYSTEM_PROMPT


class SystemPromptTests(SimpleTestCase):
    def test_asks_usage_in_the_language_being_learned(self):
        self.assertIn(
            "in source_formality_note, say the same in the source language", SYSTEM_PROMPT
        )
        self.assertIn(
            "In source_contexts, list the same situations in the same order, written in the source",
            SYSTEM_PROMPT,
        )
        self.assertIn(
            "Every field whose name starts with source_, including the items of source_contexts",
            SYSTEM_PROMPT,
        )

    def test_asks_the_playful_parts_of_the_card(self):
        self.assertIn(
            "put it in pitfall_wrong and the correct form in pitfall_right", SYSTEM_PROMPT
        )
        self.assertIn("In literal, give the word-for-word rendering", SYSTEM_PROMPT)
        self.assertIn("In imagine, write in the target", SYSTEM_PROMPT)
        self.assertIn(
            "In source_pitfall, give the same warning in the source language", SYSTEM_PROMPT
        )
        self.assertIn("source_imagine, write the same image in the source language", SYSTEM_PROMPT)
        self.assertIn("dialogue of two to four lines between speakers A and B", SYSTEM_PROMPT)
