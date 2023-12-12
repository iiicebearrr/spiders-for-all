class MaxRetryExceedError(Exception):
    def __init__(self, retries: int) -> None:
        msg = f"Max retries {retries} has been exceeded"
        super().__init__(msg)
