"""
This module implements a Lambda function that acts as a custom resource in AWS CloudFormation.

It allows you to call any boto method for any CREATE, UPDATE or DELETE CloudFormation event. If defined for the event
type it receives, the function will call a Boto3 client method specified in the CloudFormation resource properties and
sets the method response as data, which is accessible in CloudFormation via Fn::GetAtt.

The function can also retrieve the physical resource ID from the Boto3 method response using a JMESPath expression
specified in the resource properties. If the expression returns a value, the function sets the value as the resource
ID and returns it to CloudFormation.
"""

from datetime import datetime, date
import json
from types import MethodType
from typing import Any, Callable, Dict, Optional


# From requirements.txt:
import boto3
from crhelper import CfnResource
from jmespath import search
from flatdict import FlatterDict


cfn_resource = CfnResource()


def handle_param_typing(parameter):
    """
    Type-cast the given parameter to the correct type.

    This function takes a parameter and returns a type-casted version of that parameter, if necessary. The function is
    used to ensure that the parameters passed to the Boto3 method called by the Lambda function are of the correct
    type, as custom resource parameters are (wrongfully) all mapped to strings.
    @see: https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/1037

    The function takes one argument, parameter, which can be of any type. The function will recursively traverse
    dictionaries and lists and cast any values that match certain type strings. The supported type strings are
    'Type::Int', 'Type::Float', and 'Type::Bool', and the corresponding cast functions are int(), float(), and bool(),
    respectively.

    :param parameter: The parameter to type-cast. This can be of any type.

    :type parameter: Any

    :return: The type-casted parameter, with the same structure as the input parameter.

    :rtype: Any
    """

    TYPE_MAPPERS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
        'Type::Int': lambda v: int(v['Type::Int']),
        'Type::Float': lambda v: float(v['Type::Float']),
        'Type::Bool': lambda v: v['Type::Bool'].lower() in ('true', '1')
    }

    return (
        TYPE_MAPPERS[next(k for k in parameter if k in TYPE_MAPPERS)](parameter) if isinstance(parameter, dict)
        and any(k in parameter for k in TYPE_MAPPERS)
        else {k: handle_param_typing(v) for k, v in parameter.items()} if isinstance(parameter, dict)
        else [handle_param_typing(v) for v in parameter] if isinstance(parameter, list)
        else parameter
    )


@cfn_resource.create
@cfn_resource.update
@cfn_resource.delete
def handle_custom_resource_request(event: Dict[str, Any], _) -> Optional[str]:
    """
    Handle the creation, update, or deletion of the custom CloudFormation resource using the specified Boto3 method.

    :param event: A dictionary containing information about the event that triggered this function.
                  This dictionary should be a valid CloudFormation custom resource event, and contain the following
                  keys:
                    - RequestType: the CloudFormation custom resource request type (typically, Create, Update, Delete)
                    - ResponseURL: pre-signed S3 URL for the custom resource response
                    - StackId: the CloudFormation stack ID
                    - RequestId: a unique id for the request
                    - ResourceType: the resource type
                    - LogicalResourceId: the resource logical ID
                    - ResourceProperties: the resource custom properties.

    :type event: Dict[str, Any]

    :param _: An object containing information about the currently executing function and runtime environment.

    :type _: object

    :return: If the physical resource ID can be extracted from the resource properties or response, return it.
             Otherwise, return None, and let crhelper handle the generation of the physical resource ID.

    :rtype: Optional[str]
    """
    # If no update handler is specified, create a new resource.
    request_type: Optional[str] = (
        event['RequestType'] if event['RequestType'] in event['ResourceProperties'] else
        'Create' if event['RequestType'] == 'Update' and 'Create' in event['ResourceProperties']
        else None
    )

    # Check if the hook should be invoked.
    if request_type is None:
        # If both the Create and Update hooks are not supported, we still want to force to Delete operation to trigger
        # by changing the PhysicalResourceId.
        if event['RequestType'] == 'Update':
            return cfn_resource.generate_physical_id(event)

        return None

    # Get Boto3 config from resource properties.
    hook_properties: Dict[str, Any] = event['ResourceProperties'][request_type]
    client_name: str = hook_properties['Client']
    method_name: str = hook_properties['Method']
    boto_request_params: Dict[str, Any] = hook_properties.get('Parameters', {})

    client = boto3.client(client_name)  # type: ignore
    if not (hasattr(client, method_name) and isinstance(getattr(client, method_name), MethodType)):
        raise ValueError('Boto client method \'%s.%s\' does not exist.' % (client_name, method_name))

    # Call Boto3 method.
    boto_res = getattr(client, method_name)(**handle_param_typing(boto_request_params))
    # Set Boto3 method response as Data, this will be accessible in CloudFormation via Fn::GetAtt.
    # Note: Boto3 return JSON unserializable datetimes, and Cfnhelper does not escape unserializable objects to strings
    # by default, thus escaping datetimes.
    cfn_resource.Data = {
        k: v.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(v, (datetime, date)) else v
        for k, v in dict(
            FlatterDict(boto_res if isinstance(boto_res, dict) else {'Result': boto_res}, delimiter='.')
        ).items()
    }

    # If the resource PhysicalResourceId can be extracted from the resource properties or response, do so.
    if request_type in ('Create', 'Update'):
        if (physical_id_expr := hook_properties.get('PhysicalResourceId')):
            physical_id = search(physical_id_expr, boto_res)

            # Fail if the JMESPath does not return anything. Dangerous behaviour as some undelying resources may have
            # been created; but a need trade-off to prevent the custom resource to be misreferenced.
            if not physical_id:
                raise ValueError('The resource was successfully %sd, but the JMESPath expression did not return any'
                                 'result. Said resource will not be roll-backed and must be deleted manually.'
                                 % request_type.lower())

            cfn_resource.Data['Ref'] = physical_id if isinstance(physical_id, str) else json.dumps(physical_id)
            return cfn_resource.Data['Ref']

    return None


def lambda_handler(event: Dict[str, Any], context):
    """
    Entry point for the AWS Lambda function.

    :param event: A dictionary containing information about the event that triggered this function.
                  This dictionary should be a valid CloudFormation custom resource event, and contain the following
                  keys:
                    - RequestType: the CloudFormation custom resource request type (typically, Create, Update, Delete)
                    - ResponseURL: pre-signed S3 URL for the custom resource response
                    - StackId: the CloudFormation stack ID
                    - RequestId: a unique id for the request
                    - ResourceType: the resource type
                    - LogicalResourceId: the resource logical ID
                    - ResourceProperties: the resource custom properties.

    :type event: Dict[str, Any]

    :param context: An object containing information about the currently executing function and runtime environment.

    :type context: object
    """
    cfn_resource(event, context)
