import click


class BaseClickCommand(click.Command):
    pass
    ## Useful to do something after the command execution and right before exiting.
    # from click import Context
    # def invoke(self, ctx: Context) -> Any:
    #     try:
    #         result = super().invoke(ctx)
    #     finally:
    #         # Do something after the command execution and right before exiting.
    #         from ..clients.tws_api_client import disconnect
    #         disconnect()
    #     return result
