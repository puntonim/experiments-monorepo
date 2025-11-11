from typing import Any

import log_utils as logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from . import dynamodb_task, s3_utils
from .views_utils import lambda_static_init

# Objects declared outside the Lambda's handler method are part of Lambda's
# *execution environment*. This execution environment is sometimes reused for subsequent
# function invocations. Note that you can not assume that this always happens.
# Typical use cases: database connection and log init. The same db connection can be
# re-used in some subsequent function invocations. It is recommended though to add
# logic to check if a connection already exists before creating a new one.
# The execution environment also provides 512 MB of *disk space* in the /tmp directory.
# Again, this can be re-used in some subsequent function invocations.
# See: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html#static-initialization

# This Lambda is configured with 0 retries. So do raise exceptions in the view.

S3_BUCKET_NAME = "ddbq-exp"

lambda_static_init()

logger.info("DYNAMODB RETRY: LOADING")


@logger.get_adapter().inject_lambda_context(log_event=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> None:
    """
    Handler for the Lambda function meant to be triggered by
     1 DynamoDB tasks of type DDBQ_EXP_RETRY.

    It just fails the first 4 attempts,  then, on the 5th attempt, successfully
     writes a file to S3.

    Args:
        event: an AWS event, eg. API Gateway event.
        context: the context passed to the Lambda.

    The `event` is a dict (that can be casted to `DynamoDBStreamEvent`) like:
        {
            "Records": [
                {
                    "eventID": "70242b559d03f02670c872260fb540b4",
                    "eventName": "INSERT",
                    "eventVersion": "1.1",
                    "eventSource": "aws:dynamodb",
                    "awsRegion": "eu-south-1",
                    "dynamodb": {
                        "ApproximateCreationDateTime": 1762875051,
                        "Keys": {
                            "SK": {
                                "S": "35L2V0UqVVEdRESeWtizSmVii3d"
                            },
                            "PK": {
                                "S": "DDBQ_EXP_RETRY#35L2V0UqVVEdRESeWtizSmVii3d"
                            }
                        },
                        "NewImage": {
                            "SenderApp": {
                                "S": "DDBQ_EXP_PRODUCER"
                            },
                            "TaskId": {
                                "S": "DDBQ_EXP_RETRY"
                            },
                            "ExpirationTs": {
                                "N": "1762875051"
                            },
                            "SK": {
                                "S": "35L2V0UqVVEdRESeWtizSmVii3d"
                            },
                            "Payload": {
                                "M": {
                                    "text": {
                                        "S": "001"
                                    }
                                }
                            },
                            "PK": {
                                "S": "DDBQ_EXP_RETRY#35L2V0UqVVEdRESeWtizSmVii3d"
                            }
                        },
                        "SequenceNumber": "343100001972810370633791",
                        "SizeBytes": 172,
                        "StreamViewType": "NEW_IMAGE"
                    },
                    "eventSourceARN": "arn:aws:dynamodb:eu-south-1:477353422995:table/ddbq-exp-task-prod/stream/2025-11-11T13:45:49.967"
                }
            ]
        }

    The `context` is a `LambdaContext` instance with properties similar to:
        {
            "aws_request_id": "7841de32-8881-4a1d-a5a9-c84fabfd9dcb",
            "log_group_name": "/aws/lambda/patatrack-botte-prod-dynamodb-message",
            "log_stream_name": "2023/10/29/[$LATEST]0051e91dce2a47819b954d3986f8c619",
            "function_name": "patatrack-botte-prod-dynamodb-message",
            "memory_limit_in_mb": "256",
            "function_version": "$LATEST",
            "invoked_function_arn": "arn:aws:lambda:eu-south-1:477353422995:function:patatrack-botte-prod-dynamodb-message",
            "client_context": null,
            "identity": "CognitoIdentity([cognito_identity_id=None,cognito_identity_pool_id=None])",
            "_epoch_deadline_time_in_ms": 1698587123978
        }
    More info here: https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

    Example:
        To trigger this Lambda, write to the DynamoDB table arn:aws:dynamodb:eu-south-1:477353422995:table/ddbq-exp-task-prod
         a record like:
        {
          "PK": "DDBQ_EXP_RETRY#35L2V0UqVVEdRESeWtizSmVii3d",
          "SK": str(ksuid.KsuidMs()),
          "TaskId": "DDBQ_EXP_RETRY",
          "SenderApp": "DDBQ_EXP_PRODUCER",
          "ExpirationTs": 1762875051,
          "Payload": {
              "text": "001"
          }
        }

        Which in DynamoDB console would be:
        {
            "PK": {"S": "DDBQ_EXP_RETRY#35L2V0UqVVEdRESeWtizSmVii3d"},
            "SK": {"S": "35L2V0UqVVEdRESeWtizSmVii3d"},
            "TaskId": {"S": "DDBQ_EXP_RETRY"},
            "ExpirationTs": {"N": "1762875051"},
            "SenderApp": {"S": "CONTABEL"},
            "Payload": {"M": {"text": {"S": "001"}}},
        }
    """
    logger.info("DYNAMODB RETRY: START")

    # Cast the event to the proper Lambda Powertools class.
    # dynamodb_event = DynamoDBStreamEvent(event)

    try:
        for task in dynamodb_task.DdbqDynamodbRetryTask.yield_from_event(event):
            for i in range(1, 6):
                key = f"root/retry/{task.text}-retry-{i}.txt"
                does_exist = s3_utils.does_exist_in_s3(
                    bucket_name=S3_BUCKET_NAME,
                    key=key,
                )
                if not does_exist:
                    s3_utils.upload_to_s3(
                        bucket_name=S3_BUCKET_NAME,
                        key=key,
                        content=str(task.ksuid),
                    )
                    if i < 5:
                        raise Exception(f"Simulated failure #{i}")
    except dynamodb_task.ValidationError:
        raise
