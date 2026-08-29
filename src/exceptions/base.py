from typing import ClassVar


class AppError(Exception):
    code: ClassVar[str] = "internal_error"
    status_code: ClassVar[int] = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
