TCP-lite Project
Author: Ke Lu (UNI: kl3753)

1. Files in this folder
-----------------------

sender.py    : TCP-lite sender over UDP
receiver.py  : TCP-lite receiver over UDP
input.txt    : small example input file ("hello from tcp lite")

The code implements a simple Go-Back-N style TCP-lite:
- fixed MSS = 1024 bytes
- fixed window size = 4 segments
- only timeouts trigger retransmissions (no fast retransmit)
- no congestion control / flow control
- checksum field is always set to zero (not used in this project)


2. How to run locally (no Mininet, simple test)
-----------------------------------------------

Open two terminals in this folder.

Terminal 1 (start receiver first):

    python3 receiver.py output.txt

Terminal 2 (start sender):

    python3 sender.py 127.0.0.1 input.txt

Explanation:
- receiver.py listens on UDP port 8080 and writes received data to output.txt
- sender.py reads all data from input.txt and sends it reliably to the receiver
- after the program finishes, output.txt should have exactly the same content
  as input.txt.


3. How to run in Mininet (example commands)
-------------------------------------------

After starting Mininet, for example:

    sudo mn --link tc,delay='800ms',loss=15,max_queue_size=3 -x

copy this folder to the Mininet host, then in the Mininet CLI:

    # run receiver on host h2
    mininet> h2 python3 /path/to/tcp_lite_kl3753/receiver.py \
        /path/to/tcp_lite_kl3753/output.txt &

    # run sender on host h1, send to h2 (10.0.0.2)
    mininet> h1 python3 /path/to/tcp_lite_kl3753/sender.py \
        10.0.0.2 /path/to/tcp_lite_kl3753/input.txt

    # check the received file on h2
    mininet> h2 cat /path/to/tcp_lite_kl3753/output.txt

If the protocol works correctly, the content of output.txt will be the same
as input.txt, even when there is packet loss in the network.

Output:
<img width="922" height="511" alt="74d4a525d213f3bc389cb4a688536663" src="https://github.com/user-attachments/assets/bd8f0dbf-3f06-4f98-9edc-020b99e00426" />

