import math
import types
from collections import defaultdict
from collections.abc import Callable
from typing import Optional


class RegressionStatus(types.SimpleNamespace):
    def __init__(
        self,
        accepted: bool,
        rating: int,
        rating_color: str | None = None,
        improved: int | None = None,
        description: str | None = None,
        details: dict | None = None,
        details_fmt: dict | None = None,
        details_conditional_fmt: Callable | None = None,
    ):
        self.rating = rating
        self.rating_color = rating_color
        self.improved = improved
        self.description = description
        self.accepted = accepted

        self.details = details
        self.details_fmt = details_fmt
        self.details_conditional_fmt = details_conditional_fmt


def do_regression_analyze(*args, **kwargs):
    # lazy loading of hunter package ...
    from .method import hunter as analyze_method

    return analyze_method.do_regression_analyze(*args, **kwargs)
