import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localflow.formatter import clean


class TestClean(unittest.TestCase):
    def test_removes_standalone_fillers(self):
        self.assertEqual(clean("I um think uh so"), "I think so")

    def test_leading_filler_with_comma(self):
        self.assertEqual(clean("Um, hello there."), "Hello there.")

    def test_filler_between_commas_keeps_single_comma(self):
        self.assertEqual(clean("Hello, um, world"), "Hello, world")

    def test_does_not_touch_filler_substrings_inside_words(self):
        self.assertEqual(clean("The umbrella and the drummer"),
                         "The umbrella and the drummer")

    def test_capitalizes_sentence_starts(self):
        self.assertEqual(clean("hello. how are you? fine!"),
                         "Hello. How are you? Fine!")

    def test_collapses_whitespace_and_space_before_punctuation(self):
        self.assertEqual(clean("hello   world ,  again ."), "Hello world, again.")

    def test_custom_filler_list(self):
        self.assertEqual(clean("well I mean yes", fillers=["well"]), "I mean yes")

    def test_empty_and_filler_only_input(self):
        self.assertEqual(clean(""), "")
        self.assertEqual(clean("um uh hmm"), "")

    def test_case_insensitive_fillers(self):
        self.assertEqual(clean("UM, sure. UH, okay."), "Sure. Okay.")

    def test_replacements_apply_case_insensitive_whole_word(self):
        self.assertEqual(
            clean("my Local Whisperer works", replacements={"local whisperer": "LocalFlow"}),
            "My LocalFlow works",
        )

    def test_replacements_do_not_hit_substrings(self):
        self.assertEqual(clean("carting cart", replacements={"cart": "wagon"}),
                         "Carting wagon")

    def test_ensure_punctuation_appends_period(self):
        self.assertEqual(clean("check check check", ensure_punctuation=True),
                         "Check check check.")

    def test_ensure_punctuation_respects_existing_terminator(self):
        self.assertEqual(clean("all done!", ensure_punctuation=True), "All done!")
        self.assertEqual(clean("", ensure_punctuation=True), "")

    def test_spoken_exclamation_all_forms(self):
        self.assertEqual(clean("whoo-hoo exclamation exclamation.", spoken_punctuation=True),
                         "Whoo-hoo!!")
        self.assertEqual(clean("that worked exclamation mark", spoken_punctuation=True),
                         "That worked!")
        self.assertEqual(clean("yes exclamation point", spoken_punctuation=True), "Yes!")

    def test_spoken_question_mark_and_capitalization_after(self):
        self.assertEqual(clean("are you coming question mark see you soon",
                               spoken_punctuation=True),
                         "Are you coming? See you soon")

    def test_spoken_period_and_comma(self):
        self.assertEqual(clean("end of story period", spoken_punctuation=True),
                         "End of story.")
        self.assertEqual(clean("wait comma what question mark", spoken_punctuation=True),
                         "Wait, what?")

    def test_spoken_new_line(self):
        self.assertEqual(clean("first item new line second item", spoken_punctuation=True),
                         "First item\nSecond item")

    def test_spoken_punctuation_off_by_default_and_no_false_positives(self):
        self.assertEqual(clean("I have a question for you"), "I have a question for you")
        self.assertEqual(clean("end of story period"), "End of story period")

    def test_spoken_command_absorbs_whispers_own_comma(self):
        self.assertEqual(clean("really, question mark", spoken_punctuation=True),
                         "Really?")


if __name__ == "__main__":
    unittest.main()
