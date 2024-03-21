import socket
import struct
import threading
import os
import random
import time


def calculate_checksum(data):
    if isinstance(data, str):
        data = data.encode()
    return sum(data) % 256


def delete_file(folder_path, file_name): #functie de stergere a unui fisier dintr-un folder
    file_path = os.path.join(folder_path, file_name) #se compune calea completa a fisierului
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
            return True
        except OSError as e:
            print(f"Failed to delete file: {file_path}. {e}")
            return False
    else:
        print(f"The specified file does not exist: {file_path}")
        return False


def create_empty_file(folder_path, file_name):
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, file_name)
    if not os.path.exists(file_path):  # Daca nu exista fisierul se creeaza unul
        try:
            with open(file_path, 'w'):
                pass
            print(f"Created new empty file: {file_path}")
        except OSError as e:
            print(f"Failed to create empty file: {file_path}. {e}")
            return False
    else:
        print(f"File already exists: {file_path}")
    return True


def append_to_file(folder_path, file_name, data):
    file_path = os.path.join(folder_path, file_name)
    try:
        with open(file_path, 'a') as file:  # Se deschide in append mode
            file.write(data)
        print(f"Appended data to file: {file_path}")
        return True
    except OSError as e:
        print(f"Failed to append to file: {file_path}. {e}")
        return False


def read_file_content(folder_path, file_name):
    file_path = os.path.join(folder_path, file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
            return content
        except OSError as e:
            print(f"Failed to read file: {file_path}. {e}")
            return None
    else:
        print(f"The specified file does not exist: {file_path}")
        return None


class GoBackNServer:
    def __init__(self, server_ip, server_port):
        self.server_address = (server_ip, server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.server_address)
        self.folder_path = 'server_files'
        self.is_first_packet = {}
        self.TIMEOUT = 2  #Dacă, în decursul a două secunde, serverul nu primește niciun pachet de la client, atunci se consideră că a avut loc un timeout.
        os.makedirs(self.folder_path, exist_ok=True) #creare director, pt True nu arunca exceptie daca folderul exista deja

    def start(self):
        print("Server started, waiting for requests...")
        while True:
            packet, client_address = self.socket.recvfrom(1024) #se intra in ciclu infinit pt a primi, pachetul e pachet si client_address = ip4 + port
            client_thread = threading.Thread(target=self.handle_client, args=(packet, client_address)) # se creeaza un thread pentru fiecare pachet primit
            client_thread.start()

    def handle_client(self, packet, client_address):
        try:
            seq_number, filename_bytes, received_checksum, operation = struct.unpack("I32sI6s", packet[:46])
            data = packet[46:]
            filename = filename_bytes.rstrip(b'\x00').decode() #se indeparteaza caracterele \x00 si se decodeaza fisierul
            operation = operation.decode().strip('\x00') #la fel si aici

            calculated_checksum = calculate_checksum(data) #verifica daca pachetul e corupt sau nu
            if calculated_checksum != received_checksum:
                print(f"Checksum mismatch for packet {seq_number} from {client_address}")
                return


            if operation == "CREATE": #creeaza un fisier cu acelasi nume ca al celui primit de la client
                self.create_file(filename, data)
            elif operation == "MOVE":
                self.move_file(filename)
            elif operation == "DELETE":
                self.delete_file(filename)
            elif operation == "READ":
                self.read_file(filename, client_address)

            if len(data) < 1014:  # Indica ultimul pachet
                self.is_first_packet[client_address] = True
            #implementare eroare
            #if random.random() < 0.5:  # 50% chance
                #time.sleep(self.TIMEOUT + 1)  # Delay longer than the timeout period

            self.socket.sendto(struct.pack("I", seq_number), client_address) #se trimite ack-ul

        except struct.error as e:
            print(f"Error in unpacking packet: {e}")

    def move_file(self, filename):
        source_path = os.path.join(self.folder_path, filename)
        target_folder = os.path.join(self.folder_path, "moved_files")
        os.makedirs(target_folder, exist_ok=True)
        target_path = os.path.join(target_folder, filename)

        try:
            if os.path.exists(source_path):
                os.rename(source_path, target_path)
                print(f"Moved file from {source_path} to {target_path}")
                return True
            else:
                print(f"File to move does not exist: {source_path}")
                return False
        except OSError as e:
            print(f"Failed to move file: {source_path}. Error: {e}")
            return False

    def create_file(self, filename, data):
        # For CREATE operation, create a new file and write data to it.
        create_empty_file(self.folder_path, filename)
        append_to_file(self.folder_path, filename, data.decode())

    def update_file(self, filename, data):
        # For UPDATE operation, append data to the file.
        # Note: The file is cleared when the first packet of UPDATE operation is received.
        append_to_file(self.folder_path, filename, data.decode())

    def delete_file(self, filename):
        # For DELETE operation, delete the specified file.
        delete_file(self.folder_path, filename)

    def read_file(self, filename, client_address):
        # For READ operation, read the file content and send it back to the client.
        content = read_file_content(self.folder_path, filename)
        if content:
            self.socket.sendto(content.encode(), client_address)


if __name__ == "__main__":
    server = GoBackNServer('127.0.0.1', 12345)
    server.start()
