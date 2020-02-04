from abc import ABC, abstractmethod


class CompressionBase(ABC):
    """

    """
    @abstractmethod
    def compress(self, o):
        pass

    @abstractmethod
    def decompress(self, o):
        pass
