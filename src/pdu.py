import struct
from crc_ccitt import append_crc, verify_crc

TYPE_DATA = 0
TYPE_ACK = 1


def build_data_pdu(seq: int, data: bytes) -> bytes:
    header = struct.pack("!IH", seq, len(data))
    return append_crc(header + data)


def build_ack_pdu(ack_seq: int) -> bytes:
    payload = struct.pack("!BI", TYPE_ACK, ack_seq)
    return append_crc(payload)


def parse_packet(raw: bytes) -> dict:
    ok, payload = verify_crc(raw)
    if not ok or len(payload) < 1:
        return {"valid_crc": False}
    if payload[0] == TYPE_ACK:
        if len(payload) < 5:
            return {"valid_crc": False}
        _, ack = struct.unpack("!BI", payload[:5])
        return {"valid_crc": True, "type": TYPE_ACK, "ack": ack}
    if len(payload) < 6:
        return {"valid_crc": False}
    seq, dlen = struct.unpack("!IH", payload[:6])
    data = payload[6:6 + dlen]
    if len(data) != dlen:
        return {"valid_crc": False}
    return {"valid_crc": True, "type": TYPE_DATA, "seq": seq, "data": data}
