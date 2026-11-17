import re
from urllib.parse import parse_qs, urlparse

# A reasonably strong password that clears MinimumLength(12) and isn't a
# dictionary word, for tests that don't care about password content.
STRONG_PASSWORD = "Tr0ub4dor&3xplosive!"


def extract_link(body, path_fragment):
    match = re.search(rf"(http\S*{re.escape(path_fragment)}\S*)", body)
    assert match, f"No {path_fragment!r} link found in email body:\n{body}"
    return match.group(1)


def extract_query(url):
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}
