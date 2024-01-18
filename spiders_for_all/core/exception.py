class MaxRetryExceedError(Exception):
    def __init__(self, retries: int) -> None:
        msg = f"Max retries {retries} has been exceeded"
        super().__init__(msg)


class ReWriteRequiredError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
