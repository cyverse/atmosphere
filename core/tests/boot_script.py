import unittest

from django.utils.timezone import now

from core.models import BootScript


class BootScriptTestCase(unittest.TestCase):

    def setUp(self):
        # initialization goes here
        pass

    def test_special_characters_removed(self):
        str_special = "This\xc2\xb6string\xc2\xb6has\xc2\xb6special\xc2\xb6characters"
        unicode_special = u"This\xc2\xb6string\xc2\xb6has\xc2\xb6special\xc2\xb6characters"
        expected_result = "Thisstringhasspecialcharacters"
        self.assertEquals(BootScript._clean_script_text(str_special), expected_result)
        self.assertEquals(BootScript._clean_script_text(unicode_special), expected_result)
