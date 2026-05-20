"""CRC-CCITT (X.25): poly 0x1021, init 0xFFFF."""


def crc_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def append_crc(payload: bytes) -> bytes:
    c = crc_ccitt(payload)
    return payload + c.to_bytes(2, "big")


def verify_crc(packet: bytes) -> tuple[bool, bytes]:
    if len(packet) < 2:
        return False, b""
    payload, crc_bytes = packet[:-2], packet[-2:]
    expected = int.from_bytes(crc_bytes, "big")
    return crc_ccitt(payload) == expected, payload
