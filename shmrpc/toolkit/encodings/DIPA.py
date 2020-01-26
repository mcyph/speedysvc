# -*- coding: utf-8 -*-

IPA = '''
a: ɐ ɑ ɒ # A's
ae: æ
b: β θ ʙ ɓ # B's
c: ç ƈ ɔ ʗ ɕ # C's (technically open O)
d: ʠ ɖ ɗ # D's
dz: ʣ ʥ ʣ ʤ
e: ə ɜ ɛ ɘ ə ɚ ɝ ɞ ʚ ɵ # E's
f: ɸ # F's
g: ɠ ɡ ɢ ɣ ɤ ʛ ʸ ˠ # G's
h: ħ ɥ ɦ ɧ ʜ ʰ ʱ # H's
i: ɨ ɪ # I's
j: ɟ ʝ ʲ # J's
k: ƙ ʞ # K's
l: ɩ ʟ ɫ ɬ ɭ ˡ # L's
lf: ʧ
lz: ɮ
m: ɯ ɰ ɱ # M's
n: ŋ ɳ ɲ ɴ # N's
o: ø ɵ ɷ ɔ ɸ ð # Misc OE's etc
oe: œ ɶ
p: ƥ # P's
q: ð # Q's
r: ɹ ɺ ɻ ɼ ɽ ɾ ɿ ʀ ʁ ʳ ʴ ʵ ʶ # R's
s: ɕ ʂ ʃ ʄ ʅ ʆ ˢ # S's
t: ƭ ʇ ʈ # T's
ts: ʦ ʨ
u: ʉ ʊ # U's
v: ʋ ʌ # V's
w: ʍ ʷ # W's
x: χ ˣ # X's
y: ʎ ʏ # Y's
z: ʐ ʑ ʒ ʓ ž # Z's
?;\xbf: ʔ ʕ ʖ ˤ ʡ ʢ ʘ  # ?'s Special (breaks, clicks)
!: ǃ # Retroflex click ISNOT question mark!
|;\xfc: | ‖ ↗ ↘ ˥ ˦ ˧ ˨ ˩ ǀ ǁ ǂ ↓ ↑ # Digraphs
\': ʼ ˈ 
*;8:  ̋ ́ ̄ ̀ ̏ ̆ ̥ ̬ ̤ ̰ ̼ ̪ ̺ ̻ ̹ ̜ ̟ ̠ ̈ ̽ ̩ ̯ ˞̴̙̘̞̝̃̕̚ ⁿ͡ # Combining/Modifiers
,: ˌ
:;\xba: ː ˑ ˑ ‿ '''

aIPA = '''p b                t d           ʈ ɖ      c ɟ      k g      q ɢ           ʔ
m     ɱ         n         ɳ     ɲ     ŋ     ɴ         
ʙ             r ɾ         ɽ             ʀ         
ɸ β     f v     θ ð     s z     ʃ ʒ     ʂ ʐ     ç ʝ     x ɣ     χ ʁ     ħ ʕ     h ɦ
    ʋ         ɹ         ɻ     j     ɰ             
        ɬ ɮ     l         ɭ     ʎ     ʟ             
ƥ ɓ             ƭ ɗ             ƈ ʄ     ƙ ɠ     ʠ ʛ         
ʘ     ǀ         ǁ     ǃ     ǂ                     
i     y                    ɨ     ʉ                ɯ     u
        ɪ     ʏ                 ʊ             
    e     ø             ɘ     ɵ             ɤ     o
                        ə                 
        ɛ     œ             ɜ     ɞ         ʌ     ɔ
            æ                 ɐ             
                    a     ɶ             ɑ     ɒ
ʍ  w  ɥ  ʜ ʢ ʡ  ɕ  ʑ ɧ ɺʦ ʣ  ʧ  ʤ  ʨ  ʥ ɚ  ɝ
˥ ˦ ˧ ˨ ˩ ↓ ↑ ↗ ↘
ˈ ˌ ː ˑ | ‖ ‿
̥̬̋́̄̀̏̆ʰ̤̰̼̪̺̻̹̜̟̠̩̯̈̽˞̴̙̘̞̝̃̕̚ⁿˡˤˠʲʷ͡'''.replace('    ', '\t')


if False:
    aLIPA = [i for i in aIPA if i.strip()]
    print('IPA Warnings:', end=' ')
    for Char in aLIPA:
        if not Char in IPA:
            print(Char.encode('utf-8'), end=' ')
    print()

DIPA = {}

for Line in IPA.split('\n'):
    Line = Line.strip()
    if not Line: continue
    Line = Line.split('#')[0].strip()
    Key, Chars = Line.split(': ')
    for iKey in Key.split(';'):
        iKey = iKey.strip() # WARNING!
        DIPA[iKey] = [i for i in Chars if i.strip()]

if __name__ == '__main__':
    from pprint import pprint
    print((to_unicode(str(GetDAccents(DIPA)).replace("u'", '')).encode('utf-8')))
    print(GetDAccents(DIPA)['e'][1]['o'])
