from .HTMLTags import get_htm_tag

if __name__ == '__main__':
    print(get_htm_tag('<img />'))
    print(get_htm_tag('<img /'))
    print(get_htm_tag('<img'))
    print(get_htm_tag('<'))
    print(get_htm_tag('<img>'))
    
    print(get_htm_tag('<img a b=c d=\'e\' f="g" h />'))
    print(get_htm_tag('<img a = b c = \'d\' e = "f">'))
    print(get_htm_tag('<img a="&amp;">'))
    print(get_htm_tag('<img a=&amp;>'))
    print(get_htm_tag('<img a=&#x26;>'))
    print(get_htm_tag('<img a=&#38;>'))
    print(get_htm_tag('<img 66a=blah>'))
    print(get_htm_tag('<img src=http://example.com/example.png>'))
    print(get_htm_tag("""<div style='width:expression(document.body.clientWidth > 800? "800px": "auto" );'></div>"""))
    
    if True:
        #import psyco
        #psyco.full()
        import time
        t_from = time.time()
        
        # Benchmark the above function
        for i in range(50000):
            get_htm_tag('<img a b=c d=\'e\' f="g" h />')
        print(t_from-time.time())
        
