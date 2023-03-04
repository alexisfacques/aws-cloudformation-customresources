"""
This module implements a Lambda function for transforming AWS CloudFormation templates using a CloudFormation macro.

The module defines two functions:

    - `lambda_handler`: The entry point of the Lambda function, which receives an event and a context object and
      returns a dictionary with a requestId, status and fragment key. The function processes the CloudFormation
      template fragment in the "fragment" key of the event dictionary, transforming it as required and returning the
      transformed fragment in the "fragment" key of the return dictionary.

    - `replace_fragment_resources`: A helper function used by `lambda_handler` to transform the Resources section of a
      CloudFormation template fragment. The function replaces all resources in a template whose Type starts with a
      given prefix with an AWS CloudFormation Custom Resource pointing to the ServiceToken corresponding to the
      resource.
"""
import json
import os
from typing import Any, Dict


def replace_fragment_resources(resources: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the Resources section of a CloudFormation template.

    This function replaces all resources whose Type starts with a given prefix with an AWS CloudFormation Custom
    Resource.

    :param resources: A dictionary representing the CloudFormation template fragment whose Resources section
                      is to be transformed.

    :type resources: dict

    :return: A dictionary representing the transformed CloudFormation template fragment, with all resources
             whose Type starts with a given prefix replaced by an AWS CloudFormation Custom Resource.

    :rtype: dict
    """
    RESOURCE_TYPE_PREFIX: str = os.environ['RESOURCE_TYPE_PREFIX']
    RESOURCE_TYPE_SERVICE_TOKENS: Dict[str, str] = json.loads(os.environ['RESOURCE_TYPE_SERVICE_TOKENS'])

    return {
        resource_id: {
            **resource_def,
            'Type': 'AWS::CloudFormation::CustomResource',
            'Properties': {
                'ServiceToken': RESOURCE_TYPE_SERVICE_TOKENS[resource_def['Type'].lstrip(RESOURCE_TYPE_PREFIX)],
                **resource_def.get('Properties')
            }
        } if 'Type' in resource_def and resource_def['Type'].startswith(RESOURCE_TYPE_PREFIX)
        and resource_def['Type'].lstrip(RESOURCE_TYPE_PREFIX) in RESOURCE_TYPE_SERVICE_TOKENS
        else resource_def for resource_id, resource_def in resources.items()
    }


def lambda_handler(event, _):
    """
    Entry point of the AWS Lambda function.

    It receives an event and a context object, and returns a dictionary with a requestId, status and fragment key.

    :param event: A dictionary containing details of the event that triggered the Lambda function.
                  This dictionary should contain the following keys:
                    - region: The AWS region in which the event originated.
                    - accountId: The AWS account ID that generated the event.
                    - fragment: A dictionary representing the CloudFormation template fragment that
                                the function is being invoked to transform.
                    - transformId: The ID of the CloudFormation macro that is being invoked to transform the template.
                    - params: A dictionary of parameters that were passed to the CloudFormation macro.
                    - requestId: A unique ID for the request that triggered the Lambda function.
                    - templateParameterValues: A dictionary of parameter values that were passed to the CloudFormation
                                               template being transformed.

    :type event: dict

    :param _: An object containing information about the current execution environment of the Lambda function.

    :type _: object

    :return: A dictionary with the following keys:
                - requestId: The unique ID for the request that triggered the Lambda function.
                - status: A string indicating the status of the transformation. Can be "success" or "failure".
                - fragment: A dictionary representing the transformed CloudFormation template fragment.

    :rtype: dict
    """
    try:
        return {
            'requestId': event['requestId'],
            'status': 'success',
            'fragment': {
                **event['fragment'],
                'Resources': replace_fragment_resources(event['fragment']['Resources'])
            }
        }

    except Exception as err:
        return {
            'requestId': event['requestId'],
            'status': 'failure',
            'fragment': event['fragment'],
            'errorMessage': str(err)
        }
