class ArraySchemaBase:
    def __init__(self, path, load_data=False):
        pass

    def keys(self):
        L = []
        for item in dir(self):
            if isinstance(item, ArrayItem):
                L.append(item)
        return L

    def __getitem__(self, item):
        return getattr(self, item)

    def load_data(self):
        pass

    def write_data(self, **data):
        pass


class ArrayItem:
    pass


class ArrayItemMetadata:
    pass


if __name__ == '__main__':
    class MySchema(ArraySchemaBase):
        fixme = ArrayItem('uint8', ArrayItemMetadata(

        ))

    schema = MySchema(path=FIXME)
    schema.write_data(**FIXME)
    schema.load_data()

