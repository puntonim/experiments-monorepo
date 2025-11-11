"""
DYNAMODB PRODUCER PARALLEL

This scripts produces and enqueues 100 tasks
 to the DynamoDB table
 with the task id DDBQ_EXP_PARALLEL
 so that it triggers the Lambda ddbq_exp/dynamodb_parallel_view.py

Tasks have a **random and unique PKs** (partition key) because Lambda can process only
 records with different PK concurrently.

The goal is to test how many Lambdas are concurrently executed.
Notice that the configuration (in serverless.yml) `batchSize: 1` and `batchWindow: 0`
 affects concurrency.
For each single task, the Lambda just writes a file to S3 with a unique key.

This producer enqueues tasks to DynamoDB as fast as possible, using threads.

Results are explained in the main README.md.

This script took about 14-18 secs to enqueue 100 tasks, with a cold start for the Lambdas
 and DynamoDB.

Usage:
 $ poetry run python scripts/ddb_producer_parallel.py
 To measure time:
 $ gtime -pv poetry run python scripts/ddb_producer_parallel.py
"""

import concurrent.futures

import aws_dynamodb_client
import datetime_utils

from ddbq_exp.dynamodb_task import DdbqDynamodbParallelTask

TABLE_NAME = "ddbq-exp-task-prod"
SENDER_APP = "DDBQ_EXP_PRODUCER"


def main():
    # I want to enqueue 100 tasks to DynamoDB as fast as possible, so I am using
    #  25 concurrent threads, which enqueues 2 tasks each.

    # 25 concurrent `producer_worker` threads.
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        futures = list()
        for i in range(1, 101, 2):
            # Each `producer_worker` thread enqueues 2 tasks.
            futures.append(
                executor.submit(producer_worker, texts=[f"{i:03}", f"{i + 1:03}"])
            )

        # Yield a future as soon as it completes.
        for future in concurrent.futures.as_completed(futures):
            # If one of the futures raises an exception, then the scheduled futures are
            #  cancelled, and the exception is re-raised.
            # Note: we can not stop already running futures.
            if future.exception() is not None:
                ## For Python >= 3.9 (older version do not support the `cancel_futures`
                #   arg).
                executor.shutdown(cancel_futures=True)
                ## For Python <= 3.8.
                # for f in futures:
                #     # Cancel all futures that have been scheduled but not run nor
                #     #  running yet.
                #     f.cancel()
                raise future.exception()


def producer_worker(texts: list[str]):
    client = DdbqExpClient()
    for text in texts:
        client.enqueue_task(text=text)


class DdbqExpClient:
    def __init__(self):
        self.table = aws_dynamodb_client.DynamodbTable(TABLE_NAME)

    def enqueue_task(self, text: str):
        now = datetime_utils.now_utc()
        data = dict(
            text=text,
            sender_app=SENDER_APP,
            expiration_ts=round(now.timestamp()),
        )
        task = DdbqDynamodbParallelTask(**data)
        try:
            response = self.table.write(item=task.to_dict())
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
