"""ElementTree-compatible XML parsing that rejects entity declarations.

Mirrors the protection of defusedxml (not bundled with QGIS): documents that
declare entities are refused, which blocks entity expansion (billion laughs)
and external entity (XXE) attacks. Element building and serialization still
use the standard library ElementTree.
"""

from xml.parsers import expat

# Only tree building and serialization are used from ElementTree; parsing is
# done by the hardened expat parser below.
from xml.etree.ElementTree import (  # nosec B405
    Element,
    ElementTree,
    ParseError,
    TreeBuilder,
    tostring,
)

__all__ = ["Element", "ElementTree", "ParseError", "fromstring", "parse", "tostring"]


class EntitiesForbidden(ParseError):
    pass


def _forbid_entities(*_args):
    raise EntitiesForbidden("XML entity declarations are not allowed")


def _fix_name(name):
    # expat reports namespaced names as "uri}local"; ElementTree uses "{uri}local".
    return "{" + name if "}" in name else name


def _create_parser(builder):
    parser = expat.ParserCreate(namespace_separator="}")
    parser.buffer_text = True
    parser.EntityDeclHandler = _forbid_entities
    parser.UnparsedEntityDeclHandler = _forbid_entities
    parser.ExternalEntityRefHandler = _forbid_entities
    parser.StartElementHandler = lambda tag, attrs: builder.start(
        _fix_name(tag), {_fix_name(k): v for k, v in attrs.items()}
    )
    parser.EndElementHandler = lambda tag: builder.end(_fix_name(tag))
    parser.CharacterDataHandler = builder.data
    return parser


def _skip_declaration(text, start):
    quote = None
    depth = 0
    index = start
    limit = len(text)
    while index < limit:
        char = text[index]
        if quote:
            if char == quote:
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth = max(0, depth - 1)
        elif char == ">" and depth == 0:
            return index + 1
        index += 1
    return limit


def _rewrite_start_tag(text, start):
    """Keep the first occurrence of each attribute. QGIS QML sometimes repeats one."""
    limit = len(text)
    index = start + 1
    while index < limit and text[index] not in " \t\r\n/>":
        index += 1
    parts = [text[start:index]]
    seen = set()
    closing = ""
    while index < limit:
        mark = index
        while index < limit and text[index] in " \t\r\n":
            index += 1
        if index >= limit:
            parts.append(text[mark:])
            break
        if text[index] == ">":
            closing = ">"
            index += 1
            break
        if text.startswith("/>", index):
            closing = "/>"
            index += 2
            break
        name_start = index
        while index < limit and text[index] not in " \t\r\n=>/":
            index += 1
        attr_name = text[name_start:index]
        if not attr_name:
            parts.append(text[mark:])
            index = limit
            closing = ""
            break
        while index < limit and text[index] in " \t\r\n":
            index += 1
        if index >= limit or text[index] != "=":
            parts.append(text[mark:])
            index = limit
            closing = ""
            break
        index += 1
        while index < limit and text[index] in " \t\r\n":
            index += 1
        if index >= limit or text[index] not in "\"'":
            parts.append(text[mark:])
            index = limit
            closing = ""
            break
        quote = text[index]
        index += 1
        value_start = index
        while index < limit and text[index] != quote:
            index += 1
        value = text[value_start:index]
        if index < limit:
            index += 1
        if attr_name not in seen:
            seen.add(attr_name)
            parts.append(f" {attr_name}={quote}{value}{quote}")
    if closing:
        parts.append(closing)
    return "".join(parts), index


def _strip_duplicate_attributes(text):
    is_bytes = isinstance(text, (bytes, bytearray))
    data = text.decode("utf-8") if is_bytes else text
    out = []
    index = 0
    limit = len(data)
    while index < limit:
        if data.startswith("<!--", index):
            end = data.find("-->", index + 4)
            end = limit if end < 0 else end + 3
        elif data.startswith("<![CDATA[", index):
            end = data.find("]]>", index + 9)
            end = limit if end < 0 else end + 3
        elif data.startswith("<?", index):
            end = data.find("?>", index + 2)
            end = limit if end < 0 else end + 2
        elif data.startswith("<!", index):
            end = _skip_declaration(data, index)
        elif data.startswith("</", index):
            end = data.find(">", index + 2)
            end = limit if end < 0 else end + 1
        elif data[index] == "<":
            tag, index = _rewrite_start_tag(data, index)
            out.append(tag)
            continue
        else:
            out.append(data[index])
            index += 1
            continue
        out.append(data[index:end])
        index = end
    cleaned = "".join(out)
    if is_bytes:
        return cleaned.encode("utf-8")
    return cleaned


def fromstring(text, _deduped=False):
    builder = TreeBuilder()
    parser = _create_parser(builder)
    try:
        parser.Parse(text, True)
    except expat.ExpatError as ex:
        if not _deduped and "duplicate attribute" in str(ex):
            try:
                cleaned = _strip_duplicate_attributes(text)
            except UnicodeError:
                cleaned = text
            if cleaned != text:
                return fromstring(cleaned, _deduped=True)
        raise ParseError(str(ex)) from ex
    return builder.close()


def parse(source):
    if hasattr(source, "read"):
        data = source.read()
    else:
        with open(source, "rb") as f:
            data = f.read()
    return ElementTree(fromstring(data))
