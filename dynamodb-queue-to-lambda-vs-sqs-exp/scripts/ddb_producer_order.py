"""
DYNAMODB PRODUCER (FIFO) ORDER

This scripts produces and enqueues 100 tasks
 to the DynamoDB table
 with the task id DDBQ_EXP_ORDER
 so that it triggers the Lambda ddbq_exp/dynamodb_order_view.py

Tasks are built such that:
 - 40 tasks have a **random and unique PKs** (partition key), so Lambda should process
   them concurrently (Lambda process only records with different PK concurrently).
 - 5 tasks have the same PK, so Lambda should process them in FIFO order.
 - 10 tasks have the same PK, so Lambda should process them in FIFO order.
 - 15 tasks have the same PK, so Lambda should process them in FIFO order.
 - 30 tasks have the same PK, so Lambda should process them in FIFO order.
Actually the order is not FIFO, but is determined by SK (sort key) alphabetically,
 but the SKs are built with Ksuid (timestamps + random uuid that are alphabetically
 sorted by timestamp).

The goal is to test that FIFO order is respected, by comparing the creation date of
 the files in S3.
We are using the configuration (in serverless.yml) `batchSize: 1` and `batchWindow: 0`,
 so the worst condition for collecting and grouping records in batches.

For each single task, the Lambda just writes a file to S3 with a unique key.

This producer enqueues tasks to DynamoDB with threads, 1 thread for each of the items
 in the list above (eg. 1 thread for the 40 random tasks, 1 thread for the 5 FIFO tasks,
 etc.).

Results are explained in the main README.md.

This script took about 7 secs to enqueue 100 tasks, with a cold start for the Lambdas
 and DynamoDB.

Usage:
 $ poetry run python scripts/ddb_producer_order.py
 To measure time:
 $ gtime -pv poetry run python scripts/ddb_producer_order.py
"""

import concurrent.futures

import aws_dynamodb_client
import datetime_utils

from ddbq_exp.dynamodb_task import DdbqDynamodbOrderTask

TABLE_NAME = "ddbq-exp-task-prod"
SENDER_APP = "DDBQ_EXP_PRODUCER"


def main():
    # I want to enqueue 100 tasks to DynamoDB as fast as possible, so I am using
    #  25 concurrent threads, which enqueues 2 tasks each.

    # 25 concurrent `producer_worker` threads.
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        futures = list()

        # 40 concurrent tasks.
        texts = [f"{x:03}" for x in range(1, 41)]
        futures.append(
            executor.submit(producer_worker, do_process_tasks_fifo=False, texts=texts)
        )
        # 5 FIFO tasks.
        texts = [f"{x:03}" for x in range(41, 46)]
        futures.append(
            executor.submit(producer_worker, do_process_tasks_fifo=True, texts=texts)
        )
        # 10 FIFO tasks.
        texts = [f"{x:03}" for x in range(46, 56)]
        futures.append(
            executor.submit(producer_worker, do_process_tasks_fifo=True, texts=texts)
        )
        # 15 FIFO tasks.
        texts = [f"{x:03}" for x in range(56, 71)]
        futures.append(
            executor.submit(producer_worker, do_process_tasks_fifo=True, texts=texts)
        )
        # 30 FIFO tasks.
        texts = [f"{x:03}" for x in range(71, 101)]
        futures.append(
            executor.submit(producer_worker, do_process_tasks_fifo=True, texts=texts)
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


def producer_worker(do_process_tasks_fifo: bool, texts: list[str]):
    client = DdbqExpClient()
    kwargs = dict()
    if do_process_tasks_fifo:
        kwargs["do_process_task_fifo"] = True
        kwargs["fifo_group_id"] = texts[0]
    for text in texts:
        client.enqueue_task(text=text, **kwargs)


class DdbqExpClient:
    def __init__(self):
        self.table = aws_dynamodb_client.DynamodbTable(TABLE_NAME)

    def enqueue_task(
        self,
        text: str,
        do_process_task_fifo: bool = False,
        fifo_group_id: str | None = None,
    ):
        now = datetime_utils.now_utc()
        data = dict(
            text=text,
            sender_app=SENDER_APP,
            expiration_ts=round(now.timestamp()),
            do_process_task_fifo=do_process_task_fifo,
            fifo_group_id=fifo_group_id,
        )
        task = DdbqDynamodbOrderTask(**data)
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
