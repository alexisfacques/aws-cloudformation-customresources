import unittest
import os
from unittest.mock import patch
from transform.lambda_function import replace_fragment_resources


class TestTransformReplaceFragmentResources(unittest.TestCase):
    @patch.dict(os.environ, {
        'RESOURCE_TYPE_PREFIX': 'MyCustom::',
        'RESOURCE_TYPE_SERVICE_TOKENS': '{"TypeA": "arn:aws:lambda:us-east-1:123456789012:function:my-function-a"}'
    })
    @patch('json.loads', return_value={
        'TypeA': 'arn:aws:lambda:us-east-1:123456789012:function:my-function-a'
    })
    def test_replace_fragment_resources_successful_replacement(self, _):
        """replace_fragment_resources() should replace any custom resource with the proper service token."""
        input_resources = {
            'MyCustom::TypeA': {
                'Type': 'MyCustom::TypeA',
                'Properties': {
                    'Property1': 'Value1',
                    'Property2': 'Value2'
                }
            },
            'AWS::EC2::Instance': {
                'Type': 'AWS::EC2::Instance',
                'Properties': {
                    'ImageId': 'ami-0c55b159cbfafe1f0',
                    'InstanceType': 't2.micro',
                    'KeyName': 'my-key-pair',
                    'SecurityGroupIds': ['sg-0123456789abcdef']
                }
            }
        }
        expected_output = {
            'MyCustom::TypeA': {
                'Type': 'AWS::CloudFormation::CustomResource',
                'Properties': {
                    'ServiceToken': 'arn:aws:lambda:us-east-1:123456789012:function:my-function-a',
                    'Property1': 'Value1',
                    'Property2': 'Value2'
                }
            },
            'AWS::EC2::Instance': {
                'Type': 'AWS::EC2::Instance',
                'Properties': {
                    'ImageId': 'ami-0c55b159cbfafe1f0',
                    'InstanceType': 't2.micro',
                    'KeyName': 'my-key-pair',
                    'SecurityGroupIds': ['sg-0123456789abcdef']
                }
            }
        }
        output = replace_fragment_resources(input_resources)
        self.assertEqual(output, expected_output)

    @patch.dict(os.environ, {
        'RESOURCE_TYPE_PREFIX': 'MyCustom::',
        'RESOURCE_TYPE_SERVICE_TOKENS': '{}'
    })
    @patch('json.loads', return_value={})
    def test_replace_fragment_resources_ignored_replacement(self, _):
        """replace_fragment_resources() should ignore replacement if a service token is missing."""
        input_resources = {
            'MyCustom::TypeC': {
                'Type': 'MyCustom::TypeC',
                'Properties': {
                    'Property1': 'Value1',
                    'Property2': 'Value2'
                }
            }
        }
        expected_output = {
            'MyCustom::TypeC': {
                'Type': 'MyCustom::TypeC',
                'Properties': {
                    'Property1': 'Value1',
                    'Property2': 'Value2'
                }
            }
        }
        output = replace_fragment_resources(input_resources)
        self.assertEqual(output, expected_output)


if __name__ == '__main__':
    unittest.main()
