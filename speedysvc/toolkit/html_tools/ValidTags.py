import re
from .webcolors import css3_names_to_hex

RE = '^(#[0-9a-fA-F]+|rgb\(\d+%?,\d*%?,?\d*%?\)?|\d{0,2}\.?\d{0,2}(cm|em|ex|in|mm|pc|pt|px|%|,|\))?)$'
RE = re.compile(RE, re.UNICODE)

SNoClose = set(['base', 'link', 'meta', 'hr', 'br', 'img', 'embed', 'param', 'area', 'col', 'input', 
                'wbr'])

SBlockLevel = set([i.lower() for i in [
    # The following are defined as block-level elements in HTML 4
    'ADDRESS', 'BLOCKQUOTE', 'CENTER', 'DIR', 'DIV', 'DL', 'FIELDSET',
    'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
    'HR', 'ISINDEX', 'MENU', 'NOFRAMES', 'NOSCRIPT', 'OL', 'P', 'PRE', 'TABLE', 'UL',
    
    # The following elements may also be considered block-level 
    # elements since they may contain block-level elements
    'DD', 'DT', 'FRAMESET', 'LI', 'TBODY', 'TD', 'TFOOT', 'TH', 'THEAD', 'TR',
    
    # The following elements may be used as either block-level elements or inline elements.
    #'APPLET', 'BUTTON', 'DEL', 'IFRAME', 'INS', 'MAP', 'OBJECT', 'SCRIPT'
    ]])

#==============================================================================#
#                            Basic Elements/CSS                                #
#==============================================================================#

SElms = set([
  "a", "abbr", "acronym", "address", "area", "b", "bdo", "big", "blockquote",
  "br", "button", "caption", "center", "cite", "code", "col", "colgroup", "dd",
  "del", "dfn", "dir", "div", "dl", "dt", "em", "fieldset", "font", "form",
  "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "input", "ins", "kbd",
  "label", "legend", "li", "map", "menu", "ol", "optgroup", "option", "p",
  "pre", "q", "s", "samp", "select", "small", "span", "strike", "strong",
  "sub", "sup", "table", "tbody", "td", "textarea", "tfoot", "th", "thead",
  "tr", "tt", "u", "ul", "var", "wbr"])

SElmAttr = set([
    "role",
  "abbr", "accept", "accept-charset", "accesskey", "action", "align", "alt",
  "axis", "border", "cellpadding", "cellspacing", "char", "charoff", "charset",
  "checked", "cite", "class", "clear", "color", "cols", "colspan", "compact",
  "coords", "datetime", "dir", "disabled", "enctype", "for", "frame",
  "headers", "height", "href", "hreflang", "hspace", "id", "ismap", "label",
  "lang", "longdesc", "maxlength", "media", "method", "multiple", "name",
  "nohref", "noshade", "nowrap", "prompt", "readonly", "rel", "rev", "rows",
  "rowspan", "rules", "scope", "selected", "shape", "size", "span", "src",
  "start", "style", "summary", "tabindex", "target", "title", "type", "usemap",
  "valign", "value", "vspace", "width", "xml:lang"])

SWiki = set([
    'abbr','b','big','blockquote','br','caption','center','cite',
    'code','dd','del','div','dl','dt','em','font','h1','h2',
    'h3','h4','h5','h6','hr','i','ins','li','ol','p','pre',
    'rb','rp','rt','ruby', # Ruby Tags
    's','small','span','strike','strong',
    'sub','sup','table','td','th','tr','tt','u','ul','var',
    #'<!-- ... -->'
])

SCSSProp = set([
  "azimuth", "background, background-*", "border, border-*", "clear", "color",
  "cursor", "direction", "display", "elevation", "float", "font",
  "font-family", "font-size", "font-style", "font-variant", "font-weight",
  "height", "letter-spacing", "line-height", "margin, margin-*", "overflow", "overflow-x", "overflow-y",
  "padding, padding-*", "pause", "pause-after", "pause-before", "pitch",
  "pitch-range", "richness", "speak", "speak-header", "speak-numeral",
  "speak-punctuation", "speech-rate", "stress", "text-align",
  "text-decoration", "text-indent", "unicode-bidi", "vertical-align",
  "voice-family", "volume", "white-space", "width", "position", "left", "top", "bottom", "right",

  "z-index",
  "align",
  "text-size",
  "list-style",
  "list-style-type",
  "list-style-position",
  "list-style-image",
  "max-width",
  "-moz-column-width",
  "-webkit-column-width",
  "column-width",
  "word-break",
  "word-wrap",


  # CSS3 added properties
  '-moz-linear-gradient',
  '-ms-linear-gradient',
  '-o-linear-gradient',
  '-webkit-linear-gradient',
  'linear-gradient',
  'text-shadow',
  'box-shadow',
  '-webkit-box-shadow',
  'border-image',
  'text-stroke',
  'text-fill-color',
  'border-radius',
  '-moz-border-radius',
  '-webkit-border-radius',
  'opacity',
  'text-overflow',
  'appearance',
  '-webkit-appearance'


  ])

SPropVals = set(
    [
        # list-style values
        "inside", "outside", "inherit", "disc", "circle", "square", "decimal",
        "decimal-leading-zero", "lower-roman", "upper-roman", "lower-greek",
        "lower-latin", "upper-latin", "armenian", "georgian", "lower-alpha",
        "upper-alpha",

        # word-break and word-wrap
        "normal", "keep-all", "break-all", "break-word",

        "!important", "aqua", "auto", "black", "block", "blue", "bold", "both",
        "bottom", "brown", "center", "collapse", "dashed", "dotted", "fuchsia",
        "gray", "green", "italic", "left", "lime", "maroon", "medium", "navy",
        "none", "normal", "nowrap", "olive", "pointer", "purple", "red", "right",
        "silver", "solid", "teal", "top", "transparent", "underline", "white",
        "yellow"
    ]
    + list(css3_names_to_hex.keys())
)

#==============================================================================#
#                          URIs and Content Types                              #
#==============================================================================#

SURIAttrs = set([
  "action", "cite", "href", "longdesc", "src", "xlink:href", "xml:base"])

SURITypes = set([
    "//",
    "bitcoin",
    "ftp", "ftps", "sftp",
    "geo",
    "gopher", "telnet",
    "http", "https",
    "irc", "ircs",
    "magnet",
    "mailto", "mms", "tel", "sms",
    "news",
    "nntp",
    "ssh",
    "sip", "sips",
    "svn", "git",
    "xmpp",

    "urn",
    "worldwind"
])

SContentTypes = set([
  "image/gif", "image/jpg", "image/png", "text/plain"])

#==============================================================================#
#                                  MathML                                      #
#==============================================================================#

SMathML = set([
  "maction", "math", "merror", "mfrac", "mi", "mmultiscripts", "mn", "mo",
  "mover", "mpadded", "mphantom", "mprescripts", "mroot", "mrow", "mspace",
  "msqrt", "mstyle", "msub", "msubsup", "msup", "mtable", "mtd", "mtext",
  "mtr", "munder", "munderover", "none"])

SMathMLAttr = set([
  "actiontype", "align", "columnalign", "columnalign", "columnalign",
  "columnlines", "columnspacing", "columnspan", "depth", "display",
  "displaystyle", "equalcolumns", "equalrows", "fence", "fontstyle",
  "fontweight", "frame", "height", "linethickness", "lspace", "mathbackground",
  "mathcolor", "mathvariant", "mathvariant", "maxsize", "minsize", "other",
  "rowalign", "rowalign", "rowalign", "rowlines", "rowspacing", "rowspan",
  "rspace", "scriptlevel", "selection", "separator", "stretchy", "width",
  "width", "xlink:href", "xlink:show", "xlink:type", "xmlns", "xmlns:xlink"])

#==============================================================================#
#                             SVG Elements/CSS                                 #
#==============================================================================#

SSVG = set([
  "a", "animate", "animateColor", "animateMotion", "animateTransform",
  "circle", "defs", "desc", "ellipse", "font-face", "font-face-name",
  "font-face-src", "g", "glyph", "hkern", "image", "line", "linearGradient",
  "marker", "metadata", "missing-glyph", "mpath", "path", "polygon",
  "polyline", "radialGradient", "rect", "set", "stop", "svg", "switch", "text",
  "title", "tspan", "use"])

SSVGAttr = set([
  "accent-height", "accumulate", "additive", "alphabetic", "arabic-form",
  "ascent", "attributeName", "attributeType", "baseProfile", "bbox", "begin",
  "by", "calcMode", "cap-height", "class", "color", "color-rendering",
  "content", "cx", "cy", "d", "descent", "display", "dur", "dx", "dy", "end",
  "fill", "fill-rule", "font-family", "font-size", "font-stretch",
  "font-style", "font-variant", "font-weight", "from", "fx", "fy", "g1", "g2",
  "glyph-name", "gradientUnits", "hanging", "height", "horiz-adv-x",
  "horiz-origin-x", "id", "ideographic", "k", "keyPoints", "keySplines",
  "keyTimes", "lang", "marker-end", "marker-mid", "marker-start",
  "markerHeight", "markerUnits", "markerWidth", "mathematical", "max", "min",
  "name", "offset", "opacity", "orient", "origin", "overline-position",
  "overline-thickness", "panose-1", "path", "pathLength", "points",
  "preserveAspectRatio", "r", "refX", "refY", "repeatCount", "repeatDur",
  "requiredExtensions", "requiredFeatures", "restart", "rotate", "rx", "ry",
  "slope", "stemh", "stemv", "stop-color", "stop-opacity",
  "strikethrough-position", "strikethrough-thickness", "stroke",
  "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin",
  "stroke-miterlimit", "stroke-opacity", "stroke-width", "systemLanguage",
  "target", "text-anchor", "to", "transform", "type", "u1", "u2",
  "underline-position", "underline-thickness", "unicode", "unicode-range",
  "units-per-em", "values", "version", "viewBox", "visibility", "width",
  "widths", "x", "x-height", "x1", "x2", "xlink:actuate", "xlink:arcrole",
  "xlink:href", "xlink:role", "xlink:show", "xlink:title", "xlink:type",
  "xml:base", "xml:lang", "xml:space", "xmlns", "xmlns:xlink", "y", "y1", "y2",
  "zoomAndPan"])

SSVGCSSProps = set([
  "fill", "fill-opacity", "fill-rule", "stroke", "stroke-linecap",
  "stroke-linejoin", "stroke-opacity", "stroke-width"])
