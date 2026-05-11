from __future__ import annotations


class MochiError(Exception):
    pass


class MochiAuthError(MochiError):
    pass


class MochiNotFoundError(MochiError):
    pass


class MochiRateLimitError(MochiError):
    pass


class MochiServerError(MochiError):
    pass
