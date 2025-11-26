# HW4 TCP(lite) sender
# UNI : kl3753
# Name: Ke Lu

import socket
import struct
import sys
import time

MSS = 1024
WINDOW_SIZE = 4
TIMEOUT = 1.5    
RECEIVER_PORT = 8080

# header layout: seq(32) | ack(32) | flags(16) | length(16) | unused(16)
HEADER_FMT = "!IIHHH"
HEADER_LEN = struct.calcsize(HEADER_FMT)

FLAG_SYN = 0x1
FLAG_ACK = 0x2
FLAG_FIN = 0x4


def make_packet(seq, ack, flags, payload=b""):
    """build one packet with our tiny TCP header"""
    length = len(payload)
    header = struct.pack(HEADER_FMT, seq, ack, flags, length, 0)
    return header + payload


def parse_packet(data):
    """parse header fields and get payload"""
    header = data[:HEADER_LEN]
    seq, ack, flags, length, _ = struct.unpack(HEADER_FMT, header)
    payload = data[HEADER_LEN:HEADER_LEN + length]
    return seq, ack, flags, payload


def do_handshake(sock, dest_addr):
    """
    3-way handshake:
      client:  SYN(seq = 0) ----------------->
      server:  <------------- SYN+ACK(ack=1)
      client:  ACK(ack = server_seq+1) ------>
    return: first data seq
    """
    print("== Handshake start ==")
    sock.settimeout(0.5)

    my_seq = 0
    while True:
        syn = make_packet(my_seq, 0, FLAG_SYN)
        sock.sendto(syn, dest_addr)
        print("  send SYN")

        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            print("  timeout waiting SYN-ACK, resend SYN")
            continue

        rseq, rack, rflags, _ = parse_packet(data)
        if (rflags & FLAG_SYN) and (rflags & FLAG_ACK) and rack == my_seq + 1:
            print("  got SYN-ACK")
            ack = make_packet(my_seq + 1, rseq + 1, FLAG_ACK)
            sock.sendto(ack, dest_addr)
            print("  send final ACK")
            print("== Handshake done ==")
            return my_seq + 1   # first data seq


def build_segments(file_bytes, start_seq):
    """cut file into MSS sized segments, assign seq numbers"""
    segs = []
    seq = start_seq
    i = 0
    n = len(file_bytes)
    while i < n:
        chunk = file_bytes[i:i + MSS]
        segs.append((seq, chunk))
        seq += len(chunk)
        i += len(chunk)
    return segs


def send_with_gbn(sock, dest_addr, segments):
    """
    Go-Back-N sending logic.
    Only one timer for the oldest unacked packet.
    Return next_seq after the last data byte (for FIN).
    """
    if not segments:
        return 0

    base = 0            # index of the first unACKed segment
    next_to_send = 0    # index of the next segment we will send
    n = len(segments)
    timer_start = None

    sock.settimeout(0.1) 

    while base < n:
        while next_to_send < n and next_to_send - base < WINDOW_SIZE:
            seq, payload = segments[next_to_send]
            pkt = make_packet(seq, 0, 0, payload)
            sock.sendto(pkt, dest_addr)
            print(f"[SEND] index={next_to_send}, seq={seq}, len={len(payload)}")

            if base == next_to_send:
                timer_start = time.time()  # start timer for the oldest seg

            next_to_send += 1

        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            # maybe timeout? check timer
            if timer_start is not None and time.time() - timer_start >= TIMEOUT:
                print("[TIMEOUT] retransmit window base..next")
                # resend all packets in the current window
                for i in range(base, next_to_send):
                    seq, payload = segments[i]
                    pkt = make_packet(seq, 0, 0, payload)
                    sock.sendto(pkt, dest_addr)
                    print(f"[RESEND] index={i}, seq={seq}")
                timer_start = time.time()
            continue

        rseq, rack, rflags, _ = parse_packet(data)
        if rflags & FLAG_ACK:
            print(f"[RECV ACK] ack={rack}")

            while base < n:
                sseq, spayload = segments[base]
                if sseq + len(spayload) <= rack:
                    base += 1
                else:
                    break

            if base == next_to_send:
                timer_start = None
            else:
                timer_start = time.time()

    last_seq, last_payload = segments[-1]
    end_seq = last_seq + len(last_payload)
    return end_seq


def close_connection(sock, dest_addr, fin_seq):
    """
    simple connection close:
      client: FIN ---------->
      server: <------ FIN+ACK
      client: ACK ---------->
    """
    print("== Closing connection ==")
    sock.settimeout(0.5)

    while True:
        fin = make_packet(fin_seq, 0, FLAG_FIN)
        sock.sendto(fin, dest_addr)
        print(f"  send FIN, seq={fin_seq}")

        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            print("  timeout waiting FIN-ACK, resend FIN")
            continue

        rseq, rack, rflags, _ = parse_packet(data)
        if (rflags & FLAG_FIN) and (rflags & FLAG_ACK):
            print("  got FIN-ACK")
            last_ack = make_packet(rack, rseq + 1, FLAG_ACK)
            sock.sendto(last_ack, dest_addr)
            print("  send last ACK")
            break

    print("== Connection closed ==")


def main():
    if len(sys.argv) != 3:
        print("Usage: python sender.py <destination-ip> <filename>")
        sys.exit(1)

    dest_ip = sys.argv[1]
    filename = sys.argv[2]

    with open(filename, "rb") as f:
        data = f.read()
    print(f"file size = {len(data)} bytes")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest_addr = (dest_ip, RECEIVER_PORT)

    start_seq = do_handshake(sock, dest_addr)

    segments = build_segments(data, start_seq)
    end_seq = send_with_gbn(sock, dest_addr, segments)

    close_connection(sock, dest_addr, end_seq)

    sock.close()


if __name__ == "__main__":
    main()
