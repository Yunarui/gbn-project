from datetime import datetime
from pathlib import Path


class TransferLogger:
    def __init__(self, log_path: str):
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        self._f = open(log_path, "w", encoding="utf-8")
        self._send_n = 0
        self._recv_n = 0

    def log_send(self, pdu_seq: int, status: str, acked_no: int):
        self._send_n += 1
        ts = datetime.now().isoformat(timespec="milliseconds")
        self._f.write(
            f"{self._send_n}, {ts}, pdu_to_send={pdu_seq}, status={status}, ackedNo={acked_no}\n"
        )
        self._f.flush()

    def log_recv(self, pdu_exp: int, pdu_recv: int, status: str):
        self._recv_n += 1
        ts = datetime.now().isoformat(timespec="milliseconds")
        self._f.write(
            f"{self._recv_n}, {ts}, pdu_exp={pdu_exp}, pdu_recv={pdu_recv}, status={status}\n"
        )
        self._f.flush()

    def close(self):
        self._f.close()
