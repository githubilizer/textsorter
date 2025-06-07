import re

# Patterns to detect metadata lines
_METADATA_PREFIXES = ["--", "http", "Timestamp:", "Map view:", "Source:", "@"]


def _is_metadata(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    if any(line.startswith(prefix) for prefix in _METADATA_PREFIXES):
        return True
    # match two letter comment tags like cc- jj- mm-
    if re.match(r"^[A-Za-z]{2}-", line):
        return True
    return False


def extract_metadata_lines(text: str):
    """Return a list of metadata lines found in ``text``."""
    return [ln for ln in text.splitlines() if _is_metadata(ln)]


def split_segment(title: str, content: str, original_text: str, split_points):
    """Split ``content`` using ``split_points`` and duplicate metadata lines.

    Parameters
    ----------
    title : str
        Title line to prepend to each sub-segment.
    content : str
        Content lines without the title.
    original_text : str
        Complete original text for metadata extraction.
    split_points : Iterable[int]
        1-indexed positions indicating after which sentence the content should
        be split. The function converts them to zero-based indexes internally.

    Returns
    -------
    list[str]
        A list of new segments including metadata lines.
    """
    lines = content.splitlines()

    # Separate metadata lines from content lines
    metadata_lines = []
    content_lines = []
    for ln in lines:
        if _is_metadata(ln):
            metadata_lines.append(ln)
        else:
            content_lines.append(ln)

    # Combine non-metadata lines back into a single string
    content_str = "\n".join(content_lines)

    # Split into sentences for more precise splits
    sentences = re.split(r"(?<=[.!?])\s+", content_str)

    # Treat provided split points as 1-indexed positions.  Convert them to
    # zero-based indexes while ensuring they stay within valid bounds.
    split_points = sorted({max(0, int(p) - 1) for p in split_points})
    segments = []
    start = 0
    for sp in split_points:
        sp = max(0, min(sp, len(sentences) - 1))
        segment_content = " ".join(sentences[start : sp + 1]).strip()
        seg = title.strip() + "\n" + segment_content
        if metadata_lines:
            seg += "\n" + "\n".join(metadata_lines)
        segments.append(seg)
        start = sp + 1

    if start < len(sentences):
        final_content = " ".join(sentences[start:]).strip()
        seg = title.strip() + "\n" + final_content
        if metadata_lines:
            seg += "\n" + "\n".join(metadata_lines)
        segments.append(seg)

    return segments
