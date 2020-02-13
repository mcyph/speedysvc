from struct import Struct


class SHMBase:
    # Encoder for command requests
    # length of command [0-255],
    # length of arguments [0~4GB]
    request_serialiser = Struct('!HI')

    # Encoder for the command responses
    # status of response [b'+' is success, b'-' is exception occurred],
    # length of response [0-4GB]
    response_serialiser = Struct('!cI')

