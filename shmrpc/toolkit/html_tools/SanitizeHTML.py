import re
from .SanitizeCSS import sanitize_css
from .Unescape import unescape
from .ValidTags import SURIAttrs, SURITypes
from . import ValidTags


def combine(*L):
    S = set()
    for i_S in L:
        S.update(i_S)
    return S


SElms = combine(
    ValidTags.SElms,
    ValidTags.SMathML,
    ValidTags.SSVG
)
SAttr = combine(
    ValidTags.SElmAttr,
    ValidTags.SMathMLAttr,
    ValidTags.SSVGAttr
)


svg_attr_val_allows_ref = {
    'clip-path',
    'color-profile',
    'cursor',
    'fill',
    'filter',
    'marker',
    'marker-start',
    'marker-mid',
    'marker-end',
    'mask',
    'stroke'
}


svg_allow_local_href = {
    'altGlyph',
    'animate',
    'animateColor',
    'animateMotion',
    'animateTransform',
    'cursor',
    'feImage',
    'filter',
    'linearGradient',
    'pattern',
    'radialGradient',
    'textpath',
    'tref',
    'set',
    'use'
}


def sanitize_html(tag_name, D, 
                  SElms=SElms, 
                  SAttr=SAttr, 
                  SProtocols=SURITypes):
    """
    tag_name -> The tag's name
    D -> The tag's attributes dict
    DElms -> The allowed elements
    DAttr -> The allowed attributes
    DProtocols -> The allowed protocols (see Tags.DURITypes)
    """
    
    tag_name = tag_name.lower() # HACK!
    if tag_name in SElms:
        for k in list(D.keys()):
            # Delete unallowed attributes
            if not k in SAttr: 
                del D[k]
        
        for attr in SURIAttrs:
            # Validate URLs using REs
            if not attr in D: 
                continue
            
            val_unescaped = re.sub("[`\000-\040\177-\240\s]+", '', unescape(D[attr])).lower()
            
            if re.match("^[a-z0-9][-+.a-z0-9]*:",val_unescaped) and \
                (val_unescaped.split(':')[0] not in SURITypes):
                del D[attr]
        
        for attr in svg_attr_val_allows_ref:
            # SVG something something...
            if attr in D:
                D[attr] = re.sub(r'url\s*\(\s*[^#\s][^)]+?\)', ' ',
                                 unescape(D[attr]))
        
        if (tag_name in svg_allow_local_href and
            'xlink:href' in D and re.find('^\s*[^#\s].*', D['xlink:href'])):
            # ???
            # Disable SVG links?
            del D['xlink:href']
        
        if 'style' in D and D['style']:
            # Sanitize the CSS
            D['style'] = sanitize_css(D['style'])
        return tag_name, D
    
    else:
        # Don't allow!
        return None, None


if __name__ == '__main__':
    print(sanitize_html('a', {'role': 'presentation'}))

    sanitize_html('<script> do_nasty_stuff() </script>')
    #    => &lt;script> do_nasty_stuff() &lt;/script>
    sanitize_html('<a href="javascript: sucker();">Click here for $100</a>')
    sanitize_html('<a role="presentation">Click here for $100</a>')
    #    => <a>Click here for $100</a>
