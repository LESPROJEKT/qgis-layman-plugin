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


def fromstring(text):
    builder = TreeBuilder()
    parser = _create_parser(builder)
    try:
        parser.Parse(text, True)
    except expat.ExpatError as ex:
        raise ParseError(str(ex)) from ex
    return builder.close()


def parse(source):
    if hasattr(source, "read"):
        data = source.read()
    else:
        with open(source, "rb") as f:
            data = f.read()
    return ElementTree(fromstring(data))
