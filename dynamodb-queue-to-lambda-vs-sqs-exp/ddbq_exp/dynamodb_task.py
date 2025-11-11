import json
from abc import ABC, abstractmethod
from datetime import UTC, timedelta
from functools import lru_cache
from typing import Any

import datetime_utils
from boto3.dynamodb.types import TypeDeserializer
from ksuid import KsuidMs

__all__ = [
    "DdbqDynamodbParallelTask",
    "DdbqDynamodbRetryTask",
    "DDBQ_EXP_PARALLEL_TASK_ID",
    "DDBQ_EXP_ORDER_TASK_ID",
    "DDBQ_EXP_RETRY_TASK_ID",
]

DDBQ_EXP_PARALLEL_TASK_ID = "DDBQ_EXP_PARALLEL"
DDBQ_EXP_ORDER_TASK_ID = "DDBQ_EXP_ORDER"
DDBQ_EXP_RETRY_TASK_ID = "DDBQ_EXP_RETRY"


class DdbqDynamodbTaskBase(ABC):
    """
    A task enqueued to the DynamoDB Task Queue for the DynamoDB Queue to Lambda
     experiment.
    Its payload is a number as text, like "031" that will be the file name in S3.
    """

    @property
    @abstractmethod
    def TASK_ID(self):
        pass

    def __init__(
        self,
        text: str,
        sender_app: str,
        do_process_task_fifo: bool = False,
        fifo_group_id: str | None = None,
        # Eg. str(KsuidMs()) -> '2XfZrNMydhTvwyWlHdzJPdz3wuA'.
        #  And: KsuidMs.from_base62('2XfZrNMydhTvwyWlHdzJPdz3wuA').
        ksuid: KsuidMs | None = None,
        expiration_ts: int | None = None,
    ):
        """
        Args:
            text: the text to include in the task payload.
            sender_app: identifier of the sender app.
            do_process_task_fifo: True to have Lambda process this task sequentially
             in a FIFO order, together with all other tasks with do_process_task_fifo=True
             and the same fifo_group_id.
             False to maximize concurrency, so many Lambdas will process all tasks with
             do_process_task_fifo=False concurrently.
            fifo_group_id: only useful in a very rare use case: when you have 2+ groups
             of tasks that need to be processed by Lambda sequentially. You will have
             2+ concurrent Lambdas that process tasks with the same fifo_group_id
             sequentially. So it's concurrency between groups, but sequentially for
             tasks of the same group.
            ksuid: eg. str(KsuidMs()) -> '2XfZrNMydhTvwyWlHdzJPdz3wuA'; only useful in
             tests.
            expiration_ts: if you really want to customize the expiration; only useful
             in tests.
        """
        self.text = text
        self.sender_app = sender_app
        self.do_process_task_fifo = do_process_task_fifo
        self.fifo_group_id = fifo_group_id
        if not ksuid:
            # Unique ID (like UUID), but with a timestamp info in it, and
            #  alphabetically sortable by timestamp.
            # Eg. str(KsuidMs()) -> '2XfZrNMydhTvwyWlHdzJPdz3wuA'.
            #  And: KsuidMs.from_base62('2XfZrNMydhTvwyWlHdzJPdz3wuA').
            ksuid = KsuidMs()
        self.ksuid = ksuid
        # Mind that ExpirationTs is configured as automatic TTL in the DynamoDB Table.
        # Note that the deletion happens eventually, within 2 days.
        if not expiration_ts:
            # It's Unix epoch time format in seconds (UTC of course).
            ksuid_date = ksuid.datetime.astimezone(UTC)
            expiration_ts = round((ksuid_date + timedelta(hours=1)).timestamp())
        self.expiration_ts = expiration_ts

    def to_dict(self) -> dict:
        """
        Used by consumers to build the DynamoDB Item to INSERT.

        Using `aws-dynamodb-client` lib (which uses Boto3 lib) this dict will be
         converted to this JSON:
            {
                "PK": {
                    "S": "DDBQ_EXP_PARALLEL#35Ks7iXolN7F096ufa4VHzW1Zdy"
                },
                "SK": {
                    "S": "35Ks7iXolN7F096ufa4VHzW1Zdy"
                },
                "ExpirationTs": {
                    "N": "1762869932"
                },
                "Payload": {
                    "M": {
                        "text": {
                            "S": "031"  # Notice: string.
                        }
                    }
                },
                "SenderApp": {
                    "S": "DDBQ_EXP_PRODUCER"
                },
                "TaskId": {
                    "S": "DDBQ_EXP_PARALLEL"
                }
            }
        """
        data = {
            "PK": self.TASK_ID,  # + something, done later one.
            # SK is used for sorting and de-duplicating.
            "SK": None,  # str(self.ksuid), assigned later on.
            "TaskId": self.TASK_ID,
            "SenderApp": self.sender_app,
            "Payload": {
                "text": self.text,  # As string.
            },
            "ExpirationTs": self.expiration_ts,  # It's the TTL.
        }

        # Validation.
        if not isinstance(self.text, str):
            raise ValidationError(f"text must be string: {self.text}")

        if not isinstance(self.sender_app, str):
            raise ValidationError(f"SenderApp must be string: {self.sender_app}")

        if not isinstance(self.ksuid, KsuidMs):
            raise ValidationError(f"ksuid must be KsuidMs: {self.ksuid}")
        data["SK"] = str(self.ksuid)

        # Create suffix for the PK (partition key).
        # IMP: this DynamoDB record will trigger Lambda (via DynamoDB Stream). Lambda
        #  can process only records with different PK (partition key) concurrently.
        #  While records with the same PK will be processed sequentially, with the order
        #  determined by SK (sort key, alphabetically).
        # So, first, make the suffix unique (using ksuid).
        suffix = f"#{str(self.ksuid)}"
        # Second, if the consumer wants this task to be processed sequentially (FIFO)
        #  then remove the suffix, so this task will have the common PK.
        if self.do_process_task_fifo:
            suffix = ""
            # Third, if the consumer wants only the tasks in a group to be processed
            #  sequentially (FIFO) then the suffix should be fifo_group_id.
            if self.fifo_group_id:
                suffix = f"#{self.fifo_group_id}"
        data["PK"] += suffix

        try:
            datetime_utils.timestamp_to_utc_datetime(self.expiration_ts)
        except Exception as exc:
            raise ValidationError(
                f"ExpirationTs must be int timestamp: {self.expiration_ts}"
            ) from exc
        return data

    @lru_cache  # noqa: B019
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def _make_from_record(cls, record: dict) -> "DdbqDynamodbTaskBase":
        """
        Record format:
        {
            "eventID": "f397cba4486f1fded155dabc99b0fc5a",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "eu-south-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1762869932,
                "Keys": {
                    "SK": {
                        "S": "35Ks7iXolN7F096ufa4VHzW1Zdy"
                    },
                    "PK": {
                        "S": "DDBQ_EXP_PARALLEL#35Ks7iXolN7F096ufa4VHzW1Zdy"
                    }
                },
                "NewImage": {
                    "SenderApp": {
                        "S": "DDBQ_EXP_PRODUCER"
                    },
                    "TaskId": {
                        "S": "DDBQ_EXP_PARALLEL"
                    },
                    "ExpirationTs": {
                        "N": "1762869932"
                    },
                    "SK": {
                        "S": "35Ks7iXolN7F096ufa4VHzW1Zdy"
                    },
                    "Payload": {
                        "M": {
                            "text": {
                                "S": "031"
                            }
                        }
                    },
                    "PK": {
                        "S": "DDBQ_EXP_PARALLEL#35Ks7iXolN7F096ufa4VHzW1Zdy"
                    }
                },
                "SequenceNumber": "67600004285332514440945",
                "SizeBytes": 154,
                "StreamViewType": "NEW_IMAGE"
            },
            "eventSourceARN": "arn:aws:dynamodb:eu-south-1:477353422995:table/ddbq-exp-task-prod/stream/2025-11-11T13:45:49.967"
        }
        """
        event_name = record.get("eventName")
        if event_name != "INSERT":
            raise ValidationError(f"Not an INSERT DynamoDB stream event: {event_name}")

        new_image: dict = record.get("dynamodb", {}).get("NewImage", {})
        if not new_image:
            raise ValidationError(f"dynamodb > NewImage missing in record: {record}")

        pk = _deserialize(new_image.get("PK"))
        sk = _deserialize(new_image.get("SK"))
        task_id = _deserialize(new_image.get("TaskId"))
        sender_app = _deserialize(new_image.get("SenderApp"))
        payload = _deserialize(new_image.get("Payload"))
        # Mind that ExpirationTs is configured as automatic TTL.
        expiration_ts = _deserialize(new_image.get("ExpirationTs"))

        # Validation.
        hash_pos = pk.find("#") if pk.find("#") > -1 else len(pk)
        if pk[:hash_pos] != cls.TASK_ID:
            raise ValidationError(f"Invalid PK: {pk}")

        try:
            # Unfortunately it seems to never raise even for invalid strings like "XXX".
            ksuid = KsuidMs.from_base62(sk)
        except Exception as exc:
            raise ValidationError(f"SK must be KsuidMs: {sk}") from exc

        # Unfortunately KsuidMs.from_base62() seems to never raise even for invalid
        #  strings like "XXX", so we check the timestamp.
        if (
            not datetime_utils.timestamp_to_utc_datetime(int(ksuid.timestamp)).year
            >= datetime_utils.now().year - 1
        ):
            raise ValidationError(f"SK must be KsuidMs: {sk}")

        if task_id != cls.TASK_ID:
            raise ValidationError(f"Invalid TaskId: {task_id}")

        if not sender_app:
            raise ValidationError(f"Invalid SenderApp: {sender_app}")
        elif not isinstance(sender_app, str):
            raise ValidationError(f"SenderApp must be string: {sender_app}")

        if not payload:
            raise ValidationError(f"Invalid Payload: {payload}")
        elif not isinstance(payload, dict):
            raise ValidationError(f"Payload must be dict: {payload}")
        text = payload.get("text")
        if not text:
            raise ValidationError(f"Invalid text: {text}")
        elif not isinstance(text, str):
            raise ValidationError(f"text must be string: {text}")

        try:
            datetime_utils.timestamp_to_utc_datetime(int(expiration_ts))
        except Exception as exc:
            raise ValidationError(
                f"Invalid format for ExpirationTs: {expiration_ts}"
            ) from exc

        return cls(
            text=text,
            sender_app=sender_app,
            ksuid=ksuid,
            expiration_ts=expiration_ts,
        )

    @classmethod
    def yield_from_event(cls, event: dict[str, Any]):
        records = event.get("Records")
        if records is None:
            raise ValidationError('Malformed DynamoDB stream: no ["Records"]')

        for record in records:
            try:
                yield cls._make_from_record(record)
            except ValidationError:
                raise


class DdbqDynamodbParallelTask(DdbqDynamodbTaskBase):
    TASK_ID = DDBQ_EXP_PARALLEL_TASK_ID


class DdbqDynamodbOrderTask(DdbqDynamodbTaskBase):
    TASK_ID = DDBQ_EXP_ORDER_TASK_ID


class DdbqDynamodbRetryTask(DdbqDynamodbTaskBase):
    TASK_ID = DDBQ_EXP_RETRY_TASK_ID


def _deserialize(data: dict[str, Any]):
    """
    Deserialize a dict read from DynamoDB.

    See: https://boto3.amazonaws.com/v1/documentation/api/latest/_modules/boto3/dynamodb/types.html
    """
    if not data:
        return None
    return TypeDeserializer().deserialize(data)


class BaseDdbqDynamodbTaskException(Exception):
    pass


class ValidationError(BaseDdbqDynamodbTaskException):
    pass
