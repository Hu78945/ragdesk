import re

_TOKEN = re.compile(r"[a-z0-9]+(?:[_.-][a-z0-9]+)*")

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i if in into is it its "
    "me my of on or so that the their then there these this to was what when where "
    "which who why will with you your".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens; keeps identifiers like `max_concurrency` or `kst-4102` whole."""
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


def stem(token: str) -> str:
    """Crude suffix stripping (overlapping -> overlap, retries -> retri) — enough for term matching."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token
