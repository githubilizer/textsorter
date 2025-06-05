import re

# Patterns to detect metadata lines
_METADATA_PREFIXES = [
    '--',
    'http',
    'Timestamp:',
    'Map view:',
    'Source:',
    '@'
]

def _is_metadata(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    if any(line.startswith(prefix) for prefix in _METADATA_PREFIXES):
        return True
    # match two letter comment tags like cc- jj- mm-
    if re.match(r'^[A-Za-z]{2}-', line):
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
        Line indexes after which to split.

    Returns
    -------
    list[str]
        A list of new segments including metadata lines.
    """
    lines = content.splitlines()
    split_points = sorted({int(p) for p in split_points})
    metadata_lines = extract_metadata_lines(original_text)
    segments = []
    start = 0
    for sp in split_points:
        sp = max(0, min(sp, len(lines) - 1))
        segment_content = "\n".join(lines[start:sp + 1])
        seg = title.strip() + "\n" + segment_content
        for m in metadata_lines:
            seg += "\n" + m
        segments.append(seg)
        start = sp + 1
    if start < len(lines):
        final_content = "\n".join(lines[start:])
        seg = title.strip() + "\n" + final_content
        for m in metadata_lines:
            seg += "\n" + m
        segments.append(seg)
    return segments
