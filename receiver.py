# HW4 TCP(lite) receiver
# UNI : kl3753
# Name: Ke Lu

import socket
import struct
import sys

MSS = 1024
RECEIVER_PORT = 8080

HEADER_FMT = "!IIHHH"
HEADER_LEN = struct.calcsize(HEADER_FMT)

FLAG_SYN = 0x1
FLAG_ACK = 0x2
FLAG_FIN = 0x4


def make_packet(seq, ack, flags, payload=b""):
    length = len(payload)
    header = struct.pack(HEADER_FMT, seq, ack, flags, length, 0)
    return header + payload


def parse_packet(data):
    header = data[:HEADER_LEN]
    seq, ack, flags, length, _ = struct.unpack(HEADER_FMT, header)
    payload = data[HEADER_LEN:HEADER_LEN + length]
    return seq, ack, flags, payload


def do_handshake(sock):

    print("Receiver waiting for SYN")

    while True:
        data, addr = sock.recvfrom(2048)
        seq, ack, flags, payload = parse_packet(data)

        if flags & FLAG_SYN:
            print(f"  got SYN from {addr}, seq={seq}")
            synack = make_packet(0, seq + 1, FLAG_SYN | FLAG_ACK)
            sock.sendto(synack, addr)
            print("  send SYN-ACK")

            # wait for last ACK (we do not check too strictly)
            while True:
                data2, addr2 = sock.recvfrom(2048)
                s2, a2, f2, _ = parse_packet(data2)
                if (f2 & FLAG_ACK) and not (f2 & FLAG_SYN):
                    print("  got final ACK")
                    print("Handshake done")
                    return addr, 1  # data starts from byte 1


def main():
    if len(sys.argv) != 2:
        print("Usage: python receiver.py <filename>")
        sys.exit(1)

    out_filename = sys.argv[1]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", RECEIVER_PORT))
    print(f"Receiver listening on UDP port {RECEIVER_PORT}")

    # handshake
    client_addr, expected_seq = do_handshake(sock)

    # open file for writing
    f = open(out_filename, "wb")

    while True:
        data, addr = sock.recvfrom(HEADER_LEN + MSS)
        seq, ack, flags, payload = parse_packet(data)

        # handle FIN (connection close)
        if flags & FLAG_FIN:
            print(f"[RECV FIN] seq={seq}, expected={expected_seq}")
            if seq == expected_seq:
                # all data delivered
                finack = make_packet(expected_seq, seq + 1,
                                     FLAG_FIN | FLAG_ACK)
                sock.sendto(finack, client_addr)
                print("[SEND FIN-ACK] and stop")
                break
            else:
                # still missing data, just ACK what we have
                ackpkt = make_packet(0, expected_seq, FLAG_ACK)
                sock.sendto(ackpkt, client_addr)
                continue

        # normal data packet
        if len(payload) > 0:
            if seq == expected_seq:
                # in-order packet
                f.write(payload)
                expected_seq += len(payload)
                print(f"[RECV DATA] seq={seq}, len={len(payload)}, "
                      f"new expected={expected_seq}")
            else:
                # out-of-order or duplicate, simply ignore data
                print(f"[OUT-OF-ORDER] got seq={seq}, expected={expected_seq}")

            # send cumulative ACK (for GBN)
            ackpkt = make_packet(0, expected_seq, FLAG_ACK)
            sock.sendto(ackpkt, client_addr)
            print(f"[SEND ACK] ack={expected_seq}")

    f.close()
    sock.close()
    print("Receiver done")


if __name__ == "__main__":
    main()
