import unittest

from crossword_lib import akshars, build_lexicon, clue_for, is_crosswordy_word


def entry(word, sense, grammar="ना."):
    return {"word": word, "definitions": [{"grammar": grammar, "senses": [sense]}]}


class AksharsTest(unittest.TestCase):
    def test_splits_consonant_matra_and_nasal_into_one_cell(self):
        self.assertEqual(akshars("आँगन"), ["आँ", "ग", "न"])
        self.assertEqual(akshars("किताब"), ["कि", "ता", "ब"])
        self.assertEqual(akshars("संसार"), ["सं", "सा", "र"])

    def test_rejects_conjuncts(self):
        self.assertIsNone(akshars("क्षमा"))
        self.assertIsNone(akshars("पत्र"))


class WordFilterTest(unittest.TestCase):
    def test_accepts_plain_three_to_seven_akshar_words(self):
        self.assertTrue(is_crosswordy_word("किताब"))
        self.assertTrue(is_crosswordy_word("आँगन"))

    def test_rejects_ligatures_nukta_and_joiners(self):
        for word in ("विद्या", "ज्ञान", "क़लम", "क\u200dर", "र\u200cम"):
            self.assertFalse(is_crosswordy_word(word), word)

    def test_rejects_spaces_slashes_digits_and_punctuation(self):
        for word in ("घर बार", "घर/बार", "घर२", "घर-बार", "घर।"):
            self.assertFalse(is_crosswordy_word(word), word)

    def test_rejects_too_short_and_too_long(self):
        self.assertFalse(is_crosswordy_word("घर"))
        self.assertFalse(is_crosswordy_word("अलमलअलमल"))


class ClueTest(unittest.TestCase):
    def test_uses_first_clause_without_numbering_or_danda(self):
        e = entry("अँकवार", "१. अँगालो; दुइटै हातका बिच आबद्ध भएर भेट्ने स्थिति।")
        self.assertEqual(clue_for(e), "अँगालो")

    def test_strips_invisible_joiners_from_clue(self):
        e = entry("अँचार", "\u200c मसाला र अमिलोको योगबाट बनेको व्यञ्जन।")
        self.assertEqual(clue_for(e), "मसाला र अमिलोको योगबाट बनेको व्यञ्जन")

    def test_rejects_cross_references(self):
        self.assertIsNone(clue_for(entry("अँखलो", "हे. आँख्लो।")))

    def test_rejects_surnames(self):
        e = entry("थिकेपा", "नेपालको हिमाली क्षेत्रमा बसोबास गर्ने भोटे जातिको एक थर।")
        self.assertIsNone(clue_for(e))

    def test_rejects_clue_that_contains_answer(self):
        self.assertIsNone(clue_for(entry("किताब", "किताब पढ्ने ठाउँ।")))

    def test_rejects_non_noun_non_adjective(self):
        self.assertIsNone(clue_for(entry("अँकाउनु", "आँक्न लाउनु।", "प्रेक्रि.")))
        self.assertEqual(clue_for(entry("अँखडी", "पूरा; सबै।", "वि.")), "पूरा")


class LexiconTest(unittest.TestCase):
    def test_keeps_crosswordy_rows_sorted_and_deduplicated(self):
        data = [
            entry("किताब", "पढ्ने पुस्तक।"),
            entry("आँगन", "घरअगाडिको खुला ठाउँ।"),
            entry("किताब", "अर्को अर्थ।"),
            entry("विद्या", "ज्ञान।"),
            entry("अँकाउनु", "आँक्न लाउनु।", "प्रेक्रि."),
        ]
        rows = build_lexicon(data)
        self.assertEqual(
            rows,
            [
                ["आँगन", "घरअगाडिको खुला ठाउँ"],
                ["किताब", "पढ्ने पुस्तक"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
