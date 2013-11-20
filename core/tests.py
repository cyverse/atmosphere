#from django.utils import unittest
#from django.test import TestCase
#from core.models import credential
#import json
#
#
#class CredentialTests(TestCase):
#    '''
#    Test models.Credential
#    '''
#    # "Access Key", "Secret Key", "API Key"
#    KEY = ""
#    # 2ae8p0au, aw908e75iti, 120984723qwe
#    VALUE = ""
#
#    def setUp(self):
#        pass
#        #create scratch pgsql db
#
#    def tearDown(self):
#        pass
#
#    # should suceed
#    def testInit(self):
#        c = credential.Credential()
#        c.key = self.KEY
#        c.value = self.VALUE
#
#        self.assertEquals(repr(c), self.KEY + ':' + self.VALUE,
#                          "Printed representations do not match")
#
#    # should succesfully return valid JSON
#    def testJsonReturnValue(self):
#        """
#        @todo: Credential.json returns single-quoted json instead of required
#        double-quoted.
#        """
#        c = credential.Credential()
#        c.key = self.KEY
#        c.value = self.VALUE
#
#        """ is actually a dict for later serialization """
#        expected = {'key': self.KEY, 'value': self.VALUE}
#
#        self.assertDictEqual(expected, c.json,
#                            "Returned Dict is not equal to expected.")
#
#    # should fail
#    def testKeyExceedingMaxLength(self):
#        pass
#
#    # should fail
#    def testValueExceedingMaxLength(self):
#        pass
#
#    # should pass
#    def testSavingCredential(self):
#        pass
#
#    # should fail
#    def testSavingCredentialWithoutIdentity(self):
#        pass
#
#    # should fail
#    def testSavingCredentialWithUndefinedKey(self):
#        pass
#
#    # should fail
#    def testSavingCredentialWithBlankKey(self):
#        pass
#
#    # should fail
#    def testSavingCredentialWithUndefinedValue(self):
#        pass
#
#    # should fail
#    def testSavingCredentialWithBlankValue(self):
#        pass
#
#    # test malformed Key
#    # @todo: Is there any defined format??
#
#if __name__ == "__main__":
#    #import sys;sys.argv = ['', 'Test.testName']
#    unittest.main()
