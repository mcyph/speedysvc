import re
from re import IGNORECASE
from .ValidTags import SCSSProp, SPropVals, SSVGCSSProps

CHK1_RE = re.compile("""^([-:,;#%.\sa-zA-Z0-9!]|-?\w+-\w+|'[\s\w]+'|"[\s\w]+"|\(([\d,\s%]+|(rgba?)?\([\d,\s%]+\)|left|right|top|bottom)+\))*$""", IGNORECASE)
CHK2_RE = re.compile("^(\s*[-\w]+\s*:\s*[^:;]*(;|$))*$", IGNORECASE)
S_RE = re.compile("([-\w]+)\s*:\s*([^:;]*)", IGNORECASE)
URL_RE = re.compile('url\s*\(\s*[^\s)]+?\s*\)\s*', IGNORECASE)
OTHER_RE = re.compile("^(#[0-9a-fA-F]+|rgba?\(-?\d*(\.\d*)?%?,-?\d*(\.\d*)?%?,?-?\d*(\.\d*)?%?\)?|-?\d*(\.\d*)?(cm|em|ex|in|mm|pc|pt|px|%|,|\))?)$", IGNORECASE)


comma_re = '(\s*,\s*)'
num_255_re = '([0-9]{1,3})'
rgba_re = (
    '(rgba?\s*\(\s*' +
        num_255_re+comma_re +
        num_255_re+comma_re +
        num_255_re +
        ('(%s)?' % (comma_re+num_255_re)) +
    '\s*\))'
)
color_re = '('+rgba_re+'|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|'+'|'.join(SPropVals)+')'
stop_re = '('+color_re+'(\s+\d+(\.\d*)?%)?)'
stops_re = (
    '((%s)*%s)' % (
        stop_re + comma_re,
        stop_re
    )
)
position_re = '(left|right|top|bottom)'

linear_gradient_re = (
    '^(-moz-linear-gradient|-ms-linear-gradient|-o-linear-gradient|-webkit-linear-gradient|linear-gradient)\s*\(\s*' +
        position_re+comma_re +
        stops_re +
    '\s*\)\s*$'
)

#print rgba_re
#print stop_re
#print stops_re
#print position_re+comma_re+stops_re
#print linear_gradient_re


def sanitize_css(S):
    #return '' # HACK!

    # disallow urls
    S = URL_RE.sub(' ', S)

    # CHECK THIS NEXT LINE!
    # This makes it so that e.g. "width:22em; " works
    # (with a trailing semicolon), but may introduce problems!


    LOut = []
    for rule in S.split(';'):
        rule = rule.strip()
        if not rule:
            continue

        if not CHK1_RE.match(rule):
            print(('RULE REJECTED #1:', rule))
            continue
        elif not CHK2_RE.match(rule):
            print(('RULE REJECTED #2:', rule))
            continue

        LOut.append(rule)

    S = ';'.join(LOut)


    # Do a general validation check
    if not CHK1_RE.match(S):
        print(('REJECT CSS:', S))
        return ''

    if not CHK2_RE.match(S):
        print(('REJECT CSS:', S))
        return ''


    clean = []
    for prop,value in re.findall(S_RE, S):
        if not value.strip():
            continue
        
        elif prop.lower() in SCSSProp:
            # Check simple properties valid
            clean.append(prop + ': ' + value + ';')
            
        elif prop.split('-')[0].lower() in ['background','border','margin','padding', 'list-style']:
            # Check individual keywords for keys which support multiple values
            if 'gradient' in value and re.match(linear_gradient_re, value, flags=IGNORECASE):
                # Specific detection for linear gradients
                #print 'GRAD:', value
                clean.append(prop + ': ' + value + ';')

            else:
                i_value = re.sub(color_re, '', value, flags=IGNORECASE) # support rgb!

                for keyword in i_value.split():
                    if not keyword in SPropVals and \
                       not OTHER_RE.match(keyword):

                        print(('CSS KEYWORD NOT RECOGNIZED:', prop, value, keyword))

                        break

                clean.append(prop + ': ' + value + ';')
            
        elif prop.lower() in SSVGCSSProps:
            # Check in SVG before giving up
            clean.append(prop + ': ' + value + ';')

        else:
            print(('GIVING UP ON CSS:', prop, value))

    return ' '.join(clean).lower() # CHECK THE lower() IS OK! ================================================================


if __name__ == '__main__':
    print((sanitize_css('border-width: 1px 0px 1px 1px; background: url(blah)')))
    print((sanitize_css('width:22em; ')))

    print((sanitize_css("""position:absolute; height:100%; left:0px; width:208.076923077px; padding-left:5px; text-align:left; background-color:rgb(254,214,123); background-image: -moz-linear-gradient(left, rgba(255,255,255,1), rgba(254,217,106,1) 15%, rgba(254,217,106,1)); background-image: -ms-linear-gradient(left, rgba(255,255,255,1), rgba(254,217,106,1) 15%, rgba(254,217,106,1)); background-image: -o-linear-gradient(left, rgba(255,255,255,1), rgba(254,217,106,1) 15%, rgba(254,217,106,1)); background-image: -webkit-linear-gradient(left, rgba(255,255,255,1), rgba(254,217,106,1) 15%, rgba(254,217,106,1)); background-image: linear-gradient(left, rgba(255,255,255,1), rgba(254,217,106,1) 15%, rgba(254,217,106,1));""")))
