import re
import hashlib


def has_integer(line: str) -> bool:
    """Checks if a line contains an integer."""
    return any(char.isdigit() for char in line)


def is_contain_var(line: str) -> bool:
    """Checks if a line contains a variable."""
    if "month=" in line.lower().replace(" ", ""):
        return True  # special case
    line_clean = line.lower().replace(" ", "")
    if "=" in line_clean:
        # We ask if there is {, ', ", or if there is an integer in the line
        # (since integer input is allowed)
        if ("{" in line_clean or '"' in line_clean or "'" in line_clean) or has_integer(
            line
        ):
            return False
        else:
            return True
    return False


def cleanup_title(title: str) -> str:
    title = re.sub(r"[^a-zA-Z0-9]", r" ", title)
    title = re.sub(r"\s\s", r" ", title)
    title = re.sub(r"  ", r" ", title)
    title = title.strip()
    return title


def cleanup_author(author: str) -> str:
    author = author.replace("\n", " ")
    author = re.sub(r"\s\s", r" ", author)
    author = re.sub(r"  ", r" ", author)
    author = author.strip()
    return author


def get_md5_hash(fn: str) -> str:
    """Compute the MD5 hash of a file.

    Args:
        fn (str): The path to the file.

    Returns:
        str: The MD5 hash of the file.
    """
    hash_md5 = hashlib.md5()
    with open(fn, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()