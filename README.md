# The missing piece(s) of your AWS CloudFormation puzzles 🧩

This CloudFormation application provides a suite of lambda-backed custom resources and macros that extend the functionality of the CloudFormation language, simplifying and streamlining the deployment and management of AWS resources and services.

Custom resources, deployed as AWS Lambda functions, can be called during a stack's lifecycle to create, update, or delete resources outside CloudFormation-managed resources. Using these custom resources, you can deploy and manage a wide range of AWS and third-party resources and services not natively supported by CloudFormation, while utilizing the power of CloudFormation's declarative language.

AWS builders can benefit from this CloudFormation application by simplifying their deployment processes, reducing errors, and improving their ability to manage their AWS environments. The following are just a few use cases:

- 🚀 Advanced landing zone configuration with AWS Organizations.
- 🛣 Simplified Route53 subdomain delegation.
- 🪣 Creating and managing S3 objects.
- 🧩 Deploying and managing AWS resources not natively supported by CloudFormation.
- 📝 Reserving address pools in a Subnet.
- 🛠 Programmatically retrieving and setting configuration variables in your AWS environment via CloudFormation templates.
- 🔗 Integrating with third-party services to deploy and manage resources.
- 🔒 Implementing advanced security features such as automatically rotating passwords and secrets.

The only custom resource currently available is `BotoHook`. It is a custom resource that allows you to call any boto method for `CREATE`, `UPDATE`, or `DELETE` CloudFormation resource lifecycle hooks and returns the complete Boto3 method response as `Data` fields, which can be retrieved in your configuration files using `Fn::GetAtt`. The custom resource's physical resource ID can be generated using a JMESPath expression.

This repository will continue to add more CloudFormation extensions, and contributions are welcome!

## Table of contents

<!-- TOC depthFrom:1 depthTo:4 withLinks:1 updateOnSave:1 orderedList:0 -->

- [The missing piece(s) of your AWS CloudFormation puzzles 🧩](#the-missing-pieces-of-your-aws-cloudformation-puzzles-)
	- [Table of contents](#table-of-contents)
	- [Usage](#usage)
		- [`CustomResources` transform](#customresources-transform)
			- [Syntax at the top level of a template](#syntax-at-the-top-level-of-a-template)
		- [`CustomResources::Boto::Hook` resource](#customresourcesbotohook-resource)
			- [Prerequisites](#prerequisites)
			- [Syntax](#syntax)
			- [Properties](#properties)
			- [Return values](#return-values)
			- [Examples of use](#examples-of-use)
			- [Known limitiations and workarounds](#known-limitiations-and-workarounds)
	- [Installation](#installation)
		- [Easy installation using the CloudFormation `CreateStack` wizard](#easy-installation-using-the-cloudformation-createstack-wizard)
		- [From source](#from-source)
			- [Requirements](#requirements)
			- [Step-by-step installation guide](#step-by-step-installation-guide)
	- [Contributing](#contributing)
	- [License](#license)
	- [Resources and references](#resources-and-references)

<!-- /TOC -->

## Usage

### `CustomResources` transform

The `CustomResources` transform is a macro deployed alongside custom resources by this application that lets you reference said custom resources using a human-friendly `Type` instead of `AWS::CloudFormation::CustomResource` (requiring to import the `ServiceToken` ARN in your templates). When a template references `CustomResources`, and you're creating or updating stacks using change sets, the Lambda-backed macro updates all resources prefixed with `CustomResources::` with their corresponding `AWS::CloudFormation::CustomResource` and `ServiceToken`.

#### Syntax at the top level of a template

Use the `CustomResources` transform at the top level of a template. You can't use the `CustomResources` transform as an embedded transform in any other template section.

##### YAML

```yaml
Transform: CustomResources
```

### `CustomResources::Boto::Hook` resource

#### Prerequisites

##### Grant the `BotoHook` function all required permissions

You must attach all required permissions to the `BotoHook` function role for the custom resource to work as intended (Alternatively, you can manually attach any AWS-managed policies **at your own risk**). The ID of the execution role used by the Lambda function is exported as an Application output and can be imported using the `Fn::ImportValue` intrinsic function:

```yaml
SubnetCidrReservationHookPolicy:
  Type: AWS::IAM::Policy
  Properties:
    PolicyDocument:
      Version: 2012-10-17
      Statement:
      - Effect: Allow
        Action:
        - ec2:CreateSubnetCidrReservation
        - ec2:DeleteSubnetCidrReservation
        Resource:
        - "*"
    PolicyName:
      Fn::Join:
      - "-"
      - - ec2
        - subnet_cidr_reservation_mgmt
    Roles:
    - Fn::ImportValue:
        Fn::Join:
        - ":"
        - - Ref: AWS::AccountId
          - Ref: AWS::Region
          - customresources
          - botohook-function-execution-role-id
```

#### Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

##### YAML

```yaml
Type: CustomResources::Boto::Hook
Properties:
  Create:
    BotoHandlerConfig
  Update:
    BotoHandlerConfig
  Delete:
    BotoHandlerConfig
```

BotoHandlerConfig definition:
```yaml
Client: String
Method: String
PhysicalResourceId: String
Parameters: Json
```

#### Properties

- `Create`

  Specifies the configuration of the CloudFormation `CREATE` lifecycle hook Boto3 handler.

  *Required*: No  

  *Type*: BotoHandlerConfig

- `Update`

  Specifies the configuration of the CloudFormation `UPDATE` lifecycle hook Boto3 handler. If unset, the resource will call the `Create` hook handler if any.

  *Required*: No  

  *Type*: BotoHandlerConfig

- `Delete`

  Specifies the configuration of the CloudFormation `DELETE` lifecycle hook Boto3 handler.

  *Required*: No  

  *Type*: BotoHandlerConfig

- `BotoHandlerConfig.Client`
  Specifies the Boto3 client to use.

  *Required*: Yes  

  *Type*: String

- `BotoHandlerConfig.Method`

  Specifies the Boto3 method to call.

  *Required*: Yes  

  *Type*: String

- `BotoHandlerConfig.PhysicalResourceId`

  A valid JMESPath expression to retrieve the custom resource's physical resource ID from the Boto3 response.

  *Required*: No  

  *Type*: String

- `BotoHandlerConfig.Parameters`

  The Boto3 method parameters.

  *Required*: No  

  *Type*: Json

#### Return values

##### Fn::GetAtt

The `Fn::GetAtt` intrinsic function returns the Boto response of the `Create` handler (situationally, the `Update` handler).

#### Examples of use

##### Simple use-cases

###### 🪣 Create an S3 Object

You can add as many lifecycle hook handle to a `Boto::Hook` as needed:

> `BotoHook` will invoke the `Create` hook during both the resource `CREATE` and `UPDATE` lifecycle stages **unless you specify a custom `Update` handler**. As defined in the AWS Custom Resources specifications, after an `UPDATE` stage, the `DELETE` stage will be then invoked with the old parameters if the `PhysicalResourceId` returned by the custom resource handler changes.

```yaml
  PutObjectHook:
    Type: CustomResources::Boto::Hook
    Properties:
      Create:
        Client: s3
        Method: put_object
        PhysicalResourceId:
          Fn::Sub: "'s3://${BucketName}/${Key}'" # Note the simple commas. PhysicalResourceId is a JMESPath expression, not a simple string.
        Parameters:
          Bucket:
            Ref: BucketName
          Key:
            Ref: Key
          Body: |
            Hello, world!
      Delete:
        Client: s3
        Method: delete_object
        Parameters:
          Bucket:
            Ref: BucketName
          Key:
            Ref: Key
```

###### 📝 Make a subnet address pool reservation

You can use the `Fn::GetAtt` intrinsic function if you need to reference an `Output` returned by one handler in another:

```yaml
CreateSubnetCidrReservationHook:
  Type: CustomResources::Boto::Hook
  Properties:
    Create:
      Client: ec2
      Method: create_subnet_cidr_reservation
      PhysicalResourceId: SubnetCidrReservation.SubnetCidrReservationId
      Parameters:
        SubnetId:
          Ref: SubnetId
        Cidr:
          Ref: CidrBlock
        ReservationType: explicit
        Description: An IPv4 address range of subnet addresses reserved in the Subnet.
        TagSpecifications:
        - ResourceType: subnet-cidr-reservation
          Tags:
          - Key: Name
            Value: SubnetCidrReservation

DeleteSubnetCidrReservationHook:
  Type: CustomResources::Boto::Hook
  Properties:
    Delete:
      Client: ec2
      Method: delete_subnet_cidr_reservation
      Parameters:
        SubnetCidrReservationId:
          Fn::GetAtt:
          - CreateSubnetCidrReservationHook
          - SubnetCidrReservation.SubnetCidrReservationId
```

##### Advanced use-cases

When associated with AWS StackSets and AWS Organizations, `BotoHook` can be a powerful tool, used to grant organizational accounts additional capabilities, such as:
- modifying a Route53 hosted zone ID in the StackSet management account;
- getting the account's friendly name from the Organization.

To do so, you must configure cross-account invocation for the Lambda functions deployed by this application:

```yaml
OrganizationBotohookFunctionPermission:
  Type: AWS::Lambda::Permission
  Metadata:
    Description: Allow organizational accounts to invoke the BotoHook lambda-backed CloudFormation custom resource in this account.
  Properties:
    Action: lambda:InvokeFunction
    FunctionName:
      Fn::ImportValue:
        Fn::Join:
        - ':'
        - - Ref: AWS::AccountId
          - Ref: AWS::Region
          - customresources
          - botohook-service-token
    Principal: "*"
    PrincipalOrgID:
      Ref: OrganizationId
```

###### 🏢 Enable accounts of an Organization to retrieve their contact emails and friendly names

StackSets and `BotoHook` can allow you to retrieve information about your Organization management account from other organizational accounts:

```yaml
OrganizationsDescribeAccountStackSet:
  Type: AWS::CloudFormation::StackSet
  Properties:
    AutoDeployment:
      Enabled: true
      RetainStacksOnAccountRemoval: true
    Capabilities: []
    Description: An example StackSet enabling accounts in the Organization to describe accounts by ID.
    ManagedExecution:
      Active: true
    OperationPreferences:
      RegionConcurrencyType: PARALLEL
    Parameters:
    - ParameterKey: BotohookServiceToken
      ParameterValue:
        Fn::ImportValue:
          Fn::Join:
          - ":"
          - - Ref: AWS::AccountId
            - Ref: AWS::Region
            - customresources
            - botohook-service-token
    PermissionModel: SERVICE_MANAGED
    StackSetName: OrganizationsDescribeAccount
    StackInstancesGroup:
    - DeploymentTargets:
        OrganizationalUnitIds:
        - Ref: OrganizationalUnitId
      Regions:
      - Ref: AWS::Region
    TemplateBody: |
      AWSTemplateFormatVersion: 2010-09-09
      Description: Get the friendly account name in the Organization it belongs to.
      Parameters:
        BotohookServiceToken:
          AllowedPattern: ^arn:[^\s:]+:lambda:[^\s:]+:[0-9]{12}:function:[^\s:]+$
          ConstraintDescription: You must specify a valid AWS Lambda function Amazon Resource Name (ARN).
          Description: The Amazon Resource Name (ARN) of this account's 'BotoHook' function.
          Type: String
      Resources:
        # This will execute on the StackSet management account.
        OrganizationsDescribeAccountHook:
          Type: AWS::CloudFormation::CustomResource
          Properties:
            ServiceToken:
              Ref: BotohookServiceToken
            Create:
              Client: organizations
              Method: describe_account
              PhysicalResourceId: Account.Name
              Parameters:
                AccountId:
                  Ref: AWS::AccountId
```

###### 🛣 Simplify Route53 subdomain delegation in an Organization using CloudFormation StackSets

StackSets and `BotoHook` enable advanced configuration patterns for Organizations, such as automated Route53 subdomain delegation:

```yaml
OrganizationsDelegateRoute53SubdomainStackSet:
  Type: AWS::CloudFormation::StackSet
  Properties:
    AutoDeployment:
      Enabled: true
      RetainStacksOnAccountRemoval: true
    Capabilities: []
    Description: An example StackSet delegating subdomains to accounts of an organization
    ManagedExecution:
      Active: true
    OperationPreferences:
      RegionConcurrencyType: PARALLEL
    Parameters:
    - ParameterKey: BotohookServiceToken
      ParameterValue:
        Fn::ImportValue:
          Fn::Join:
          - ":"
          - - Ref: AWS::AccountId
            - Ref: AWS::Region
            - customresources
            - botohook-service-token
    PermissionModel: SERVICE_MANAGED
    StackSetName: OrganizationsDelegateRoute53Subdomain
    StackInstancesGroup:
    - DeploymentTargets:
        OrganizationalUnitIds:
        - Ref: OrganizationalUnitId
      Regions:
      - Ref: AWS::Region
    TemplateBody: |
      AWSTemplateFormatVersion: 2010-09-09
      Description: Get the friendly account name in the Organization it belongs to.
      Parameters:
        BotohookServiceToken:
          AllowedPattern: ^arn:[^\s:]+:lambda:[^\s:]+:[0-9]{12}:function:[^\s:]+$
          ConstraintDescription: You must specify a valid AWS Lambda function Amazon Resource Name (ARN).
          Description: The Amazon Resource Name (ARN) of this account's 'BotoHook' function.
          Type: String
        OrganizationDomainName:
          Description: The fully qualified top-level domain name to configure on Route53.
          Type: String
          AllowedPattern: ^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\.{0,1}$
          ConstraintDescription: You must specify a fully qualified domain name, for example, www.example.com.
        OrganizationHostedZoneId:
          AllowedPattern: ^Z[0-9A-Z]{1,31}$
          ConstraintDescription: You must specify a valid AWS Route53 hosted zone identifier (ID).
          Description: The identifier (ID) of the AWS Route53 hosted zone for the given domain.
          Type: String
      Resources:
        OrganizationsDescribeAccountHook:
          Type: AWS::CloudFormation::CustomResource
          Properties:
            ServiceToken:
              Ref: BotohookServiceToken
            Create:
              Client: organizations
              Method: describe_account
              PhysicalResourceId: Account.Name
              Parameters:
                AccountId:
                  Ref: AWS::AccountId
        HostedZone:
          Type: AWS::Route53::HostedZone
          Properties:
            HostedZoneConfig:
              Comment:
                Fn::Sub:
                - A public hosted zone routing traffic on the internet for domain '${OrganizationSubDomainName}'.
                - OrganizationSubDomainName:
                    Fn::Join:
                    - .
                    - - Fn::GetAtt:
                        - OrganizationsDescribeAccountHook
                        - Account.Name
                      - Ref: OrganizationDomainName
            Name:
              Fn::Join:
              - .
              - - Fn::GetAtt:
                  - OrganizationsDescribeAccountHook
                  - Account.Name
                - Ref: OrganizationDomainName
        OrganizationChangeResourceRecordSetsNameHook:
          Type: AWS::CloudFormation::CustomResource
          Properties:
            ServiceToken:
              Ref: BotohookServiceToken
            Create:
              Client: route53
              Method: change_resource_record_sets
              PhysicalResourceId: ChangeInfo.Id
              Parameters:
                HostedZoneId:
                  Ref: OrganizationHostedZoneId
                ChangeBatch:
                  Changes:
                  - Action: CREATE
                    ResourceRecordSet:
                      Name:
                        Fn::Join:
                        - .
                        - - Fn::GetAtt:
                            - OrganizationsDescribeAccountHook
                            - Account.Name
                          - Ref: OrganizationDomainName
                      Type: NS
                      TTL:
                        Type::Int: 300
                      ResourceRecords:
                      - Value:
                          Fn::Select:
                          - 0
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 1
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 2
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 3
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
            Update:
              Client: route53
              Method: change_resource_record_sets
              PhysicalResourceId: ChangeInfo.Id
              Parameters:
                HostedZoneId:
                  Ref: OrganizationHostedZoneId
                ChangeBatch:
                  Changes:
                  - Action: UPSERT
                    ResourceRecordSet:
                      Name:
                        Fn::Join:
                        - .
                        - - Fn::GetAtt:
                            - OrganizationsDescribeAccountHook
                            - Account.Name
                          - Ref: OrganizationDomainName
                      Type: NS
                      TTL:
                        Type::Int: 300
                      ResourceRecords:
                      - Value:
                          Fn::Select:
                          - 0
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 1
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 2
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 3
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
            Delete:
              Client: route53
              Method: change_resource_record_sets
              PhysicalResourceId: ChangeInfo.Id
              Parameters:
                HostedZoneId:
                  Ref: OrganizationHostedZoneId
                ChangeBatch:
                  Changes:
                  - Action: DELETE
                    ResourceRecordSet:
                      Name:
                        Fn::Join:
                        - .
                        - - Fn::GetAtt:
                            - OrganizationsDescribeAccountHook
                            - Account.Name
                          - Ref: OrganizationDomainName
                      Type: NS
                      TTL:
                        Type::Int: 300
                      ResourceRecords:
                      - Value:
                          Fn::Select:
                          - 0
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 1
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 2
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers
                      - Value:
                          Fn::Select:
                          - 3
                          - Fn::GetAtt:
                            - HostedZone
                            - NameServers

```

#### Known limitiations and workarounds

- [Lambda-backed CustomResource's ResourceProperties converts int and boolean properties to strings](https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/1037). This can be a problem for strictly typed APIs. `BotoHook` implements intrinsic-function-like syntax to force the type of parameters. It supports the following types:
  - Integers:
    ```yaml
    TTL:
      Type::Int: "300"
    # is transformed to:
    TTL: 300
    ```  
  - Floats:
    ```yaml
    Ratio:
      Type::Float: "0.8"
    # is transformed to:
    Ratio: 0.8
    ```  
  - Booleans:
    ```yaml
    EncryptionEnabled:
      Type::Bool: "true"
    # is transformed to:
    EncryptionEnabled: true
    ```

## Installation

### Easy installation using the CloudFormation `CreateStack` wizard

You can easily deploy and test the latest version of application using the CloudFormation `CreateStack` wizard: [Click here to deploy this application to your AWS Account](https://eu-west-1.console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/create/review?templateURL=https://public-177754923675-eu-west-1.s3.eu-west-1.amazonaws.com/customresources/406e1f6dab8108886f2f0990fcc4db1d.template&param_TransformCustomResourcesPrefix=CustomResources%3A%3A).

### From source

#### Requirements

- [AWS CLI](https://aws.amazon.com/cli/) installed and configured with appropriate permissions
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) installed

#### Step-by-step installation guide

Install the application with AWS SAM CLI as follows:

- Clone the repository to your local machine. Open a terminal and navigate to the root directory of the cloned repository.

- Build the application using AWS SAM:
  ```sh
  sam build --template-file customresources.template.yml
  ```

- Package the CloudFormation application by running the following command:
  ```sh
  sam package --s3-bucket <your-s3-bucket-name> --template-file customresources.template.yml --output-template-file packaged.yaml
  ```
  > Replace `<your-s3-bucket-name>` with the name of an S3 bucket in your AWS account.

- Deploy the CloudFormation application by running the following command:
  ```sh
  sam deploy --template-file packaged.yaml --stack-name <your-stack-name> --capabilities CAPABILITY_NAMED_IAM
  ```
  > Replace `<your-stack-name>` with a unique name for your CloudFormation stack

Alternatively, you can also let SAM guide you through this process:

```sh
sam build --template-file customresources.template.yml --guided && sam deploy
```

Once the CloudFormation stack has been created, you can instanciate custom resources by defining them in your CloudFormation templates.

## Contributing

Thank you for considering contributing to this project! Bug reports, feature requests, and code contributions are welcome.

## License

This project is licensed under the terms of the MIT license.

```
MIT License

Copyright (c) 2023 Alexis Facques

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

For more information on the MIT License, see [opensource.org/licenses/MIT](https://opensource.org/licenses/MIT).

## Resources and references

- [Boto3 custom resource and macro original project](https://github.com/awslabs/aws-cloudformation-templates/tree/master/aws/services/CloudFormation/MacrosExamples/Boto3/lambda);
