# -*- coding: utf-8 -*-
import re
import zhon.cedict


simplified = re.compile('[%s]' % (
    zhon.cedict.simp
))
traditional = re.compile('[%s]' % (
    zhon.cedict.trad
))


def hanzi_get_type(s):
    """
    Get the most likely hanzi variant for `s`,
    "simp", "trad" or "both
    """

    D = {
        'simp': simplified.sub('', s),
        'trad': traditional.sub('', s)
    }

    if len(D['simp']) == len(D['trad']):
        return 'both'
    elif len(D['simp']) < len(D['trad']):
        return 'simp'
    else:
        return 'trad'


def get_simp_trad(multi_translit, s):
    typ = hanzi_get_type(s)
    #print typ

    if typ == 'both':
        return s, s
    elif typ == 'simp':
        return s, multi_translit.translit('zh', 'zh_Hant', s)
    else:
        return multi_translit.translit('zh_Hant', 'zh', s), s


if __name__ == '__main__':
    simp, trad = get_simp_trad('王先生是中國人')
    print(simp, trad)

    simp, trad = get_simp_trad('他说中文。')
    print(simp, trad)
