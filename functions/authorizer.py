"""
Copyright 2015-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

     http://aws.amazon.com/apache2.0/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
"""
from __future__ import print_function
import logging
from pprint import pprint
import boto3
from botocore.exceptions import ClientError
import re
import os
import json

def lambda_handler(event, context):
    # Do not print the auth token unless absolutely necessary
    # print("Client token: " + event['authorizationToken'])
    # print("Method ARN: " + event['methodArn'])

    """
    Validate the token. This could be accomplished in a number of ways:
      1. Call out to OAuth provider
      2. Decode a JWT token inline
      3. Lookup in a self-managed DB
    """
    token = event['authorizationToken']
    principal_result = validate_token(token)
    if not principal_result:
        raise Exception('Unauthorized')
    else:
        principalId = principal_result

    # You can send a 401 Unauthorized response to the client by failing like so
    # raise Exception('Unauthorized
    #
    # If the token is valid, a policy must be generated which will allow or deny access to the client
    #
    # If access is denied, the client will recieve a 403 Access Denied response
    # If access is allowed, API Gateway will proceed with the backend integration configured on the method that was called
    #
    # This function must generate a policy that is associated with the recognized principal user identifier
    # depending on your use case, you might store policies in a DB, or generate them on the fly
    #
    # Keep in mind, the policy is cached for 5 minutes by default (TTL is configurable in the authorizer
    # and will apply to subsequent calls to any method/resource in the RestApi
    # made with the same token


    # Example policy below allows access to all resources in the RestApi
    #
    # Get the various components for the policy from the event['methodArn']
    tmp = event['methodArn'].split(':')
    apiGatewayArnTmp = tmp[5].split('/')
    awsAccountId = tmp[4]
    # Create policy
    policy = AuthPolicy(principalId, awsAccountId)
    # Inject / overwrite keys we're not hardcoding in the class above above
    policy.restApiId = apiGatewayArnTmp[0]
    policy.region = tmp[3]
    policy.stage = apiGatewayArnTmp[1]
    policy.allowAllMethods()
    # Allow to specific methods
    # policy.allowMethod(HttpVerb.GET, "/pets/*")

    # Finally, build the policy
    authResponse = policy.build()

    # New! -- add additional key-value pairs associated with the authenticated principal
    # these are made available by APIGW like so: $context.authorizer.<key>
    # additional context is cached
    context = {
        'key': 'value', # $context.authorizer.key -> value
        'number' : 1,
        'bool' : True
    }
    # context['arr'] = ['foo'] <- this is invalid, APIGW will not accept it
    # context['obj'] = {'foo':'bar'} <- also invalid

    authResponse['context'] = context

    return authResponse

class HttpVerb:
    GET     = "GET"
    POST    = "POST"
    PUT     = "PUT"
    PATCH   = "PATCH"
    HEAD    = "HEAD"
    DELETE  = "DELETE"
    OPTIONS = "OPTIONS"
    ALL     = "*"

class AuthPolicy(object):
    awsAccountId = ""
    """ The AWS account id the policy will be generated for. This is used to create the method ARNs"""

    principalId = ""
    """ The principal used for the policy, this should be a unique identifier for the end user """

    version = "2012-10-17"
    """ The policy version used for the evaluation. This should always be '2012-10-17' """

    pathRegex = "^[/.a-zA-Z0-9-\*]+$"
    """ The regular expression used to validate resource paths for the policy """

    """
    These are the internal lists of allowed and denied methods. These are lists
    of objects and each object has 2 properties: A resource ARN and a nullable
    conditions statement.

    The build method processes these lists and generates the approriate
    statements for the final policy
    """
    allowMethods = []
    denyMethods = []

    restApiId = "<<restApiId>>"
    """ Replace the placeholder value with a default API Gateway API id to be used in the policy.
    Beware of using '*' since it will not simply mean any API Gateway API id, because stars will greedily expand over '/' or other separators.
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html for more details. """

    region = "<<region>>"
    """ Replace the placeholder value with a default region to be used in the policy.
    Beware of using '*' since it will not simply mean any region, because stars will greedily expand over '/' or other separators.
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html for more details. """

    stage = "<<stage>>"
    """ Replace the placeholder value with a default stage to be used in the policy.
    Beware of using '*' since it will not simply mean any stage, because stars will greedily expand over '/' or other separators.
    See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html for more details. """

    def __init__(self, principal, awsAccountId):
        self.awsAccountId = awsAccountId
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []

    def _addMethod(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resourcePattern = re.compile(self.pathRegex)
        if not resourcePattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)

        if resource[:1] == "/":
            resource = resource[1:]

        resourceArn = ("arn:aws:execute-api:" +
            self.region + ":" +
            self.awsAccountId + ":" +
            self.restApiId + "/" +
            self.stage + "/" +
            verb + "/" +
            resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })

    def _getEmptyStatement(self, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }

        return statement

    def _getStatementForEffect(self, effect, methods):
        """This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy."""
        statements = []

        if len(methods) > 0:
            statement = self._getEmptyStatement(effect)

            for curMethod in methods:
                if curMethod['conditions'] is None or len(curMethod['conditions']) == 0:
                    statement['Resource'].append(curMethod['resourceArn'])
                else:
                    conditionalStatement = self._getEmptyStatement(effect)
                    conditionalStatement['Resource'].append(curMethod['resourceArn'])
                    conditionalStatement['Condition'] = curMethod['conditions']
                    statements.append(conditionalStatement)

            statements.append(statement)

        return statements

    def allowAllMethods(self):
        """Adds a '*' allow to the policy to authorize access to all methods of an API"""
        self._addMethod("Allow", HttpVerb.ALL, "*", [])

    def denyAllMethods(self):
        """Adds a '*' allow to the policy to deny access to all methods of an API"""
        self._addMethod("Deny", HttpVerb.ALL, "*", [])

    def allowMethod(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy"""
        self._addMethod("Allow", verb, resource, [])

    def denyMethod(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy"""
        self._addMethod("Deny", verb, resource, [])

    def allowMethodWithConditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._addMethod("Allow", verb, resource, conditions)

    def denyMethodWithConditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._addMethod("Deny", verb, resource, conditions)

    def build(self):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
            (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId' : self.principalId,
            'policyDocument' : {
                'Version' : self.version,
                'Statement' : []
            }
        }

        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Allow", self.allowMethods))
        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Deny", self.denyMethods))

        return policy

class SecretsManagerSecret:
    """Encapsulates Secrets Manager functions."""
    def __init__(self, secret_name):
        """
        :param secret_name: A Boto3 Secrets Manager secret.
        """
        self.secretsmanager_client = boto3.client('secretsmanager')
        self.name = secret_name
        self.logger = logging.getLogger(__name__)

    def get_value(self, stage=None):
        """
        Gets the value of a secret.

        :param stage: The stage of the secret to retrieve. If this is None, the
                      current stage is retrieved.
        :return: The value of the secret. When the secret is a string, the value is
                 contained in the `SecretString` field. When the secret is bytes,
                 it is contained in the `SecretBinary` field.
        """
        if self.name is None:
            raise ValueError

        try:
            kwargs = {'SecretId': self.name}
            if stage is not None:
                kwargs['VersionStage'] = stage
            response = self.secretsmanager_client.get_secret_value(**kwargs)
            response = json.loads(response['SecretString'])

            self.logger.info("Got value for secret %s.", self.name)
        except ClientError:
            self.logger.exception("Couldn't get value for secret %s.", self.name)
            raise
        else:
            return response

def validate_token(token_to_validate):
    """
    Check if <<token_to_validate>> is one of the tokens in our secrets.

    Return a principal to show which one matched, or False if there is no match
    """

    secret_object = SecretsManagerSecret(os.environ['secret_name'])
    known_bearer_tokens = secret_object.get_value()

    for this_client, this_secret in known_bearer_tokens.items():
        if token_to_validate == this_secret:
            return this_client
    return False

if __name__ == "__main__":
    event = {
        'authorizationToken': 'foobar',
        'methodArn': 'pretend:method:arn:from:caller:foo/bar'
    }

    print(json.dumps(lambda_handler(event, {})))
