"""
DYNAMODB PRODUCER RETRY

This scripts produces and enqueues 1 tasks
 to the DynamoDB table
 with the task id DDBQ_EXP_RETRY
 so that it triggers the Lambda ddbq_exp/dynamodb_retry_view.py

The Lambda source code is written such that it fails the first 4 attempts and on the
 5th retry it succeeds. It keeps track of retries writing files to S3.

Results are explained in the main README.md.

This script took about 1 sec to run.

Usage:
 $ poetry run python scripts/ddb_producer_retry.py
"""

import aws_dynamodb_client
import datetime_utils

from ddbq_exp.dynamodb_task import DdbqDynamodbRetryTask

TABLE_NAME = "ddbq-exp-task-prod"


def main():
    client = DdbqExpClient()
    client.enqueue_task(text="001")


class DdbqExpClient:
    def enqueue_task(
        self,
        text: str,
        sender_app: str = "DDBQ_EXP_PRODUCER",
        table_name: str = TABLE_NAME,
    ):
        table = aws_dynamodb_client.DynamodbTable(table_name)
        now = datetime_utils.now_utc()
        data = dict(
            text=text,
            sender_app=sender_app,
            expiration_ts=round(now.timestamp()),
        )
        task = DdbqDynamodbRetryTask(**data)
        try:
            response = table.write(item=task.to_dict())
        # List all known exceptions.
        except aws_dynamodb_client.BotoAuthError:
            raise
        except aws_dynamodb_client.TableDoesNotExist:
            raise
        except aws_dynamodb_client.InvalidPutItemMethodParameter:
            raise
        except aws_dynamodb_client.PrimaryKeyConstraintError:
            raise
        except aws_dynamodb_client.EndpointConnectionError:
            raise
        # response like:
        # {'ResponseMetadata': {
        #     'RequestId': 'AEMBQ9DAB9PGQ6KNQAUDK5DFKNVV4KQNSO5AEMVJF66Q9ASUAAJG',
        #     'HTTPStatusCode': 200,
        #     'HTTPHeaders': {'connection': 'keep-alive', 'content-length': '2',
        #                     'content-type': 'application/x-amz-json-1.0',
        #                     'date': 'Sat, 01 Nov 2025 13:55:40 GMT', 'server': 'Server',
        #                     'x-amz-crc32': '2745614147',
        #                     'x-amzn-requestid': 'AEMBQ9DAB9PGQ6KNQAUDK5DFKNVV4KQNSO5AEMVJF66Q9ASUAAJG'},
        #     'RetryAttempts': 0}}
        return response


if __name__ == "__main__":
    print("START")
    main()
    print("END")
