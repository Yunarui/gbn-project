class ErrorChannel:
    def __init__(self, error_rate: int, lost_rate: int):
        self.error_rate = error_rate
        self.lost_rate = lost_rate
        self._counter = 0

    def process_outgoing(self, pdu: bytes) -> bytes | None:
        self._counter += 1
        if self.lost_rate > 0 and self._counter % self.lost_rate == 0:
            return None
        if self.error_rate > 0 and self._counter % self.error_rate == 0:
            b = bytearray(pdu)
            if len(b) > 4:
                b[-3] ^= 0xFF
            return bytes(b)
        return pdu
