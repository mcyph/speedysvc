# -*- coding: utf-8 -*-

kana = ' ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなに'\
       'ぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔゕゖ  ゙゚゛゜ゝゞゟ'\
       '゠ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒ'\
       'ビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶヷヸヹヺ・ーヽヾヿ'

SKana = set()
for char in kana:
    SKana.add(char)


def is_kana(s):
    for i in s:
        if i not in SKana:
            return 0
    return 1


def contains_kana(s):
    for i in s:
        if i in SKana:
            return 1
    return 0
