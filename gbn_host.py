import socket
import threading
import time
from pathlib import Path

from channel import ErrorChannel
from config_loader import load_config
from logger import TransferLogger
from pdu import TYPE_ACK, TYPE_DATA, build_ack_pdu, build_data_pdu, parse_packet


class GBNHost:
    def __init__(self, config_path: str):
        self.cfg = load_config(config_path)
        self.mod = 1 << self.cfg["seq_bits"]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.cfg["udp_port"]))
        self.peer = (self.cfg["peer_host"], self.cfg["peer_port"])
        self.channel = ErrorChannel(self.cfg["error_rate"], self.cfg["lost_rate"])
        role = self.cfg["role"]
        Path("logs").mkdir(exist_ok=True)
        self.log = TransferLogger(f"logs/{role}_transfer.log")
        self.send_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.expected_seq = self.cfg["init_seq"] % self.mod
        self.recv_buffer = bytearray()
        self.recv_done = False
        self.chunks = self._read_file_chunks()
        self.base = 0
        self.next_seq = 0
        self.window = self.cfg["sw_size"]
        self.timeout_s = self.cfg["timeout_ms"] / 1000.0
        self.send_done = len(self.chunks) == 0
        self.stats = {"timeouts": 0, "retransmits": 0, "new_sends": 0}

    def _read_file_chunks(self) -> list[bytes]:
        path = Path(self.cfg["send_file"])
        data = path.read_bytes()
        size = min(self.cfg["data_size"], 4096)
        return [data[i:i + size] for i in range(0, len(data), size)] or [b""]

    def _seq_no(self, index: int) -> int:
        return (self.cfg["init_seq"] + index) % self.mod

    def _send_udp(self, pdu: bytes):
        maybe = self.channel.process_outgoing(pdu)
        if maybe is not None:
            self.sock.sendto(maybe, self.peer)

    def _sender_thread(self):
        timer_start = None
        while not self.stop_event.is_set():
            with self.send_lock:
                if self.send_done:
                    time.sleep(0.01)
                    continue
                while self.next_seq < self.base + self.window and self.next_seq < len(self.chunks):
                    seq = self._seq_no(self.next_seq)
                    pdu = build_data_pdu(seq, self.chunks[self.next_seq])
                    self._send_udp(pdu)
                    acked = self._seq_no(self.base) if self.base < len(self.chunks) else seq
                    self.log.log_send(seq, "New", acked)
                    self.stats["new_sends"] += 1
                    self.next_seq += 1
                    if timer_start is None:
                        timer_start = time.time()
                if timer_start and (time.time() - timer_start) >= self.timeout_s:
                    if self.base < self.next_seq:
                        self.stats["timeouts"] += 1
                        for i in range(self.base, self.next_seq):
                            seq = self._seq_no(i)
                            pdu = build_data_pdu(seq, self.chunks[i])
                            self._send_udp(pdu)
                            acked = self._seq_no(self.base)
                            self.log.log_send(seq, "TO", acked)
                            self.stats["retransmits"] += 1
                    timer_start = time.time()
            time.sleep(0.005)

    def _handle_ack(self, ack_seq: int):
        with self.send_lock:
            base_seq = self._seq_no(self.base)
            if self.next_seq == 0:
                return

            def in_window(s, b, n):
                return (s - b) % self.mod <= (n - b) % self.mod

            hi = self._seq_no(self.next_seq - 1)
            if in_window(ack_seq, base_seq, hi):
                while self.base < self.next_seq and in_window(ack_seq, self._seq_no(self.base), ack_seq):
                    self.base += 1
                if self.base >= len(self.chunks):
                    self.send_done = True

    def _receiver_loop(self):
        self.sock.settimeout(0.2)
        end_wait_start = None
        while not self.stop_event.is_set():
            try:
                raw, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                if self.recv_done and self.send_done:
                    if end_wait_start is None:
                        end_wait_start = time.time()
                    elif time.time() - end_wait_start > 2.0:
                        break
                continue
            pkt = parse_packet(raw)
            if not pkt.get("valid_crc"):
                self.log.log_recv(self.expected_seq, -1, "DataErr")
                continue
            if pkt["type"] == TYPE_ACK:
                self._handle_ack(pkt["ack"])
                continue
            if pkt["type"] != TYPE_DATA:
                continue
            seq = pkt["seq"]
            if seq == self.expected_seq:
                self.recv_buffer.extend(pkt["data"])
                self.log.log_recv(self.expected_seq, seq, "OK")
                self.expected_seq = (self.expected_seq + 1) % self.mod
                ack = build_ack_pdu((self.expected_seq - 1) % self.mod)
                self._send_udp(ack)
            else:
                self.log.log_recv(self.expected_seq, seq, "NoErr")
                last_ack = (self.expected_seq - 1) % self.mod
                if self.expected_seq != self.cfg["init_seq"] % self.mod or len(self.recv_buffer) > 0:
                    self._send_udp(build_ack_pdu(last_ack))
        Path(self.cfg["recv_file"]).parent.mkdir(parents=True, exist_ok=True)
        Path(self.cfg["recv_file"]).write_bytes(bytes(self.recv_buffer))
        self.recv_done = True

    def run(self):
        print(f"[{self.cfg['role']}] Listening UDP {self.cfg['udp_port']}, peer {self.peer}")
        print(f"[{self.cfg['role']}] Sending {self.cfg['send_file']} -> peer")
        print(f"[{self.cfg['role']}] Receiving -> {self.cfg['recv_file']}")
        t = threading.Thread(target=self._sender_thread, daemon=True)
        t.start()
        self._receiver_loop()
        self.stop_event.set()
        t.join(timeout=2)
        self.log.close()
        self.sock.close()
        print(f"[{self.cfg['role']}] Done. PDUs={len(self.chunks)}, TO={self.stats['timeouts']}")


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: 1820232048project1.exe config\\host1.ini")
        sys.exit(1)
    GBNHost(sys.argv[1]).run()


if __name__ == "__main__":
    main()
