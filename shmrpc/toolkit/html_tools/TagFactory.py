from .HTMLTags import output_htm


def get_tag_factories(s):
    L = []
    for tag in s.lower().split(','):
        L.append(get_tag_factory(tag))
    return L


def get_tag_factory(tag):
    def fn(*args, **kwargs):
        return Tag(tag, *args, **kwargs)
    return fn


class Tag:
    def __init__(self, tag, content, **DAttr):
        """
        Allows basic creation of HTML tags 
        using an object-oriented interface
        
        e.g. Tag('div', content, class_='my_class', 
                 style="display: none")
        
        -> <div class="my_class" style="display: none">(content)</div>
        """
        L = self.L = []
        self.tag = tag
        
        if content:
            L.append(content)
        
        new_D = {}
        for key, value in DAttr:
            # Make "class_" -> "class" 
            # (as "class" is a reserved keyword)
            new_D[key.rstrip('_')] = value
        self.DAttr = new_D
        
    def add(self, *elms):
        self.L.extend(elms)
        return elms[0]
    
    def to_html(self):
        L = []
        
        # TODO: Fix <br/> etc! =================================
        L.append(output_htm(self.tag, xhtml=False, D=self.DAttr, 
                            sanitize=False, output_tag=True))
        
        for elm in self.L:
            if isinstance(elm, str):
                L.append(elm)
            else:
                L.append(elm.to_html())
        
        L.append('</%s>' % self.tag)
        return ''.join(L)
    