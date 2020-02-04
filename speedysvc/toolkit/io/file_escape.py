from input import inpPytranslit

ASCII = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"


def esc(S, Spaces=True):
    try:
        S = inpPytranslit.Translit('Any to Latin', S)
        S = inpPytranslit.Translit('Accents to Any', S).replace('^', '').replace('`', '').replace('^', '').replace('<', '').replace('>', '')
    except: 
        print('ERROR IN TRANSLITERATION!')
    
    print(S.encode('utf-8', 'replace'))
    
    for i in '<>"#%{}|\^~[]`;/?:@=&!*':
        S = S.replace(i, '-')
    
    R = []
    for i in S:
        if i not in ASCII: 
            R.append('-')
        else: 
            R.append(i)
    
    S = ''.join(R)
    if Spaces: 
        S = S.replace(' ', '-')
    S = S.replace('--', '-')
    return S
