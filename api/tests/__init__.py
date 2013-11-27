"""
Common functions used by all API test cases
"""

def verify_expected_output(test_client, api_out, expected_out):
    """
    Using the output from the api:
    {'key1':'val1','key2':'random_val2'}
    and the expected output:
    {'key1':'val1','key2':''}

    1. Verify that all keys in expected output appear in the api
    2. If the value for the expected output is known, the api value must match
    """
    for key in expected_out.keys():
        test_client.assertTrue(api_out.has_key(key))
        if expected_out.get(key):
            test_client.assertEqual(api_out[key], expected_out[key])

