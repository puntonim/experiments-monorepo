import log_utils as logger

# Global var so it can be imported in conftest.py and its level can be changed in order
#  not to log in tests.
powertools_logger = logger.PowertoolsLoggerAdapter()
# Configure the logging only once.
_IS_LOGGER_CONFIGURED = False


def lambda_static_init():
    """
    To be used across al Lambdas in this repo.

    This fn is part of a Lambda *execution environment* and is run during Lambda
     static init:
     https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html#static-initialization

    Typical use cases: database connection and log init. The same db connection can be
     re-used in some subsequent function invocations. It is recommended though to add
     logic to check if a connection already exists before creating a new one.
    """
    _log_init()
    # _db_init()  # Great place where to init the db.


def _log_init():
    global _IS_LOGGER_CONFIGURED
    if _IS_LOGGER_CONFIGURED:
        return

    # IMP: this logging configuration should be done asap in the Lambda lifecycle.
    #  If there is any log statement done with `utils-monorepo/log-utils` (so a
    #  statement like `logger.info()`) before this block, then this will raise
    #  `AlreadyConfigured`.
    #  Typically, this would happen if such log statement is at module-level in
    #  on of the imports above (before) this block, from one of my libs that uses
    #  `log-utils` or a module in this repo.
    #  To resolve, just move that import statement after the invocation of this fn.
    powertools_logger.configure_default(
        #  Mind that "service" (and not "app") is the exact term used by
        #   aws_lambda_powertools.Logger.
        service_name="DynamoDB Queue to Lambda experiment",
        service_version="0.0.1",
        is_verbose=False,
    )
    try:
        logger.set_adapter(powertools_logger)
    except logger.log_adapter.AlreadyConfigured as exc:
        raise logger.log_adapter.AlreadyConfigured(
            "There is a log statement with `utils-monorepo/log-utils` before this code"
            " block, likely at module-level in an imported module; if so, then move"
            " such import after this code block"
        ) from exc
    logger.debug("Logger initialized")
    _IS_LOGGER_CONFIGURED = True
