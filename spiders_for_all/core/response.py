from pydantic import BaseModel


class Response(BaseModel):
    def raise_for_status(self):
        raise NotImplementedError()
