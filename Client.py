import socket
import struct
import time
import os


def calculate_checksum(data):
    if isinstance(data, str):
        data = data.encode()
    return sum(data) % 256


class GoBackNClient:
    def __init__(self, server_ip, server_port):
        self.server_address = (server_ip, server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.WINDOW_SIZE = 4
        self.TIMEOUT = 2  # Timeout in seconds
        self.PACKET_SIZE = 1024  # Packet size in bytes

    def read_file_chunks(self, file_path):
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(self.PACKET_SIZE - 46)  # Reserve bytes for headers
                if not chunk:
                    break
                yield chunk

    def send_packet(self, operation, filename, data, seq_number):
        checksum = calculate_checksum(data)
        filename_bytes = filename.encode().ljust(32, b'\x00')  # fisierul se transforma in bytes
        try:
            packet = struct.pack("I32sI6s", seq_number, filename_bytes, checksum, operation.encode()) + data #creare pachet plus data de 900+ octeti
            self.socket.sendto(packet, self.server_address)
            print(f"Sent packet {seq_number}")
        except struct.error as e:
            print(f"Error in packing data: {e}")
        except socket.error as e:
            print(f"Error in sending packet: {e}")

    def go_back_n(self, operation, file_path):
        filename = os.path.basename(file_path) #nume fisier extras din cale

        if operation in ["CREATE", "UPDATE"]:
            file_chunks = list(self.read_file_chunks(file_path)) #face o lista cu fragmentele din fisier
        else:
            file_chunks = [b'']  # Dummy data for operations without file content

        num_packets = len(file_chunks)

        next_to_send = 0 #este indexul următorului pachet care trebuie trimis,
        ack_expected = 0 #este indexul pachetului pentru care se așteaptă un ACK

        if operation == "READ":
            self.send_packet(operation, filename, b'', 0)  # trimite cerere de citire
            self.receive_file_content(filename)  # se ocupa de primirea continutului
        else:
            while ack_expected < num_packets:
                while next_to_send < ack_expected + self.WINDOW_SIZE and next_to_send < num_packets:
                    self.send_packet(operation, filename, file_chunks[next_to_send], next_to_send)
                    next_to_send += 1

                self.socket.settimeout(self.TIMEOUT) #in cazul timeoutul se revine la ultimul pachet trimis(resetare next_to_send) cu succes si se retrimite celalalt.
                try:
                    ack_packet, _ = self.socket.recvfrom(1024) #verifica daca e un pachet de ack
                    ack, = struct.unpack("I", ack_packet)
                    print(f"ACK received: {ack}")
                    ack_expected = ack + 1
                except socket.timeout:
                    print(f"Timeout, go back from {ack_expected}")
                    next_to_send = ack_expected #se reseteaza next to send daca se intampla timeout-> de aici provine go-back-n

    def receive_file_content(self, filename):
        content, _ = self.socket.recvfrom(1024)  #ia continutul fisierului si il decodeaza
        print("Received file content:\n", content.decode())


if __name__ == "__main__":
    client = GoBackNClient('127.0.0.1', 12345)

    # Example usage
    operation = "CREATE"  # or "CREATE", "READ", "DELETE", "MOVE"
    file_path = './pisica.txt'
    client.go_back_n(operation, file_path)
