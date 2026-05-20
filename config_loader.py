import configparser
from pathlib import Path


def load_config(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    has_section = any(
        line.strip().startswith("[") and line.strip().endswith("]")
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(";")
    )
    if not has_section:
        text = "[DEFAULT]\n" + text
    cfg = configparser.ConfigParser()
    cfg.read_string(text)
    sec = cfg["DEFAULT"] if cfg.has_section("DEFAULT") else cfg[cfg.sections()[0]]

    def get_int(key, default=None):
        return int(sec.get(key, default))

    def get_str(key, default=None):
        return sec.get(key, default)

    return {
        "role": get_str("Role", "host"),
        "udp_port": get_int("UDPPort"),
        "peer_host": get_str("PeerHost", "127.0.0.1"),
        "peer_port": get_int("PeerPort"),
        "send_file": get_str("SendFile"),
        "recv_file": get_str("RecvFile"),
        "data_size": get_int("DataSize", 1024),
        "error_rate": get_int("ErrorRate", 0),
        "lost_rate": get_int("LostRate", 0),
        "sw_size": get_int("SWSize", 4),
        "init_seq": get_int("InitSeqNo", 1),
        "timeout_ms": get_int("Timeout", 1000),
        "seq_bits": get_int("SeqBits", 8),
    }
