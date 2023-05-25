import re


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
