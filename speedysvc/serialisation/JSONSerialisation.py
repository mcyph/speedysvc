import json


class JSONSerialisation:
    """
    A class which allows serialising to json.
    Unlike PickleSerialisation, does not allow
    some custom class types, and doesn't allow
    for tuples/int's etc as dict keys.

    I generally prefer to use JSON other other
    kinds of serialisation for its often-stated
    pros: it's fast enough (though slower than
    msgpack/pickle), human-readable, and potentially
    can be used in other languages than just python.
    """

    name = 'json'
    mimetype = 'application/json'

    @staticmethod
    def dumps(o):
        return json.dumps(o).encode('utf-8')

    @staticmethod
    def loads(o):
        return json.loads(o.decode('utf-8'))
