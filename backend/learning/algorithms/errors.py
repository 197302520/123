from __future__ import annotations


class AlgorithmInputError(ValueError):
    """A stable, user-facing validation or runtime capability error."""

    def __init__(self, message: str, *, code: str = "invalid_input", path: str = "parameters") -> None:
        super().__init__(message)
        self.code = code
        self.path = path

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": str(self)}
