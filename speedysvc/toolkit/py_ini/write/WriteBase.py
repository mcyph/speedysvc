from .conv_to_str import conv_to_str


class WriteBase:
    use_colons = False

    def sort_key(self, i):
        if isinstance(i, str):
            return i.lower()
        return i

    def write_D(self, path, D):
        with open(path, 'w', encoding='utf-8') as f:
            for key, sub_D in list(D.items()):
                if not isinstance(key, (list, tuple)):
                    key = [key]

                if len(key)==1 and key[0].strip()==key[0]:
                    key = '[%s]' % key[0]
                else:
                    key = repr([conv_to_str(i) for i in key])

                if self.use_colons:
                    # Add a python-esque ":" after headings
                    key = '%s:' % key

                f.write('%s\n' % key)
                f.write('%s\n\n' % self.process_section(key, sub_D))

    def process(self, section, D):
        raise NotImplementedError
