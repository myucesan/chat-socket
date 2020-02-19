import socket
import constants as constants
import signal
import threading
from protocol import Protocol

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Define the server from beginning so it can be accessed by other files
server.bind((constants.HOST, constants.PORT))

clients = dict()

def receive(client_socket):
    receive_command = ""
    while True:
        data = client_socket.recv(1).decode()
        if data == "\n":
            return receive_command
        receive_command += data

def exists(name):
    for row in clients.values():
        if name == row["name"]:
            return True
    return False

def handle_client_requests(client_socket, client_addr):
    global clients
    while True:
        try:
            request = receive(client_socket)
            request = request.split(" ", 1)
            if request is not None:
                response = None
                if request[0] == Protocol.request_handshake.value:
                    name = request[1]
                    if len(clients.keys()) == constants.MAX_CLIENTS:
                        response = Protocol.busy.value + "\n"
                    elif " " in name:
                        response = Protocol.bad_request_header.value + "\n"
                    elif exists(name):
                        response = Protocol.in_use.value + "\n"
                    else:
                        clients.update({client_addr: {"name": name, "socket": client_socket}})
                        response = Protocol.response_handshake.value + " " + name + "\n"
                else:
                    if clients.get(client_addr) is None:
                        response = Protocol.bad_request_header.value + "\n"
                    elif request[0] == Protocol.request_who.value:
                        online_list = ""
                        for row in clients.values():
                            online_list += row["name"] + ","
                        online_list = online_list[:-1]
                        response = Protocol.response_who.value + " " + online_list + "\n"
                    elif request[0] == Protocol.request_send.value:
                        request = request[1].split(" ", 1)
                        dest_user = None
                        name = request[0]
                        message = request[1]
                        for row in clients.values():
                            if row["name"] == name:
                                dest_user = row
                        if dest_user is None:
                            response = Protocol.unknown.value + "\n"
                        else:
                            message = Protocol.delivery.value + " " + name + " " + message + "\n"
                            dest_user["socket"].sendall(message.encode())
                            response = Protocol.response_send.value + "\n" 
                    else:
                        response = Protocol.bad_request_body.value + "\n"
                client_socket.sendall(response.encode())
        except ConnectionResetError:
            clients.pop(client_addr)
            break


if __name__ == '__main__':
    server.listen()
    while True:
        client_socket, client_addr = server.accept()
        threading.Thread(target=handle_client_requests, args=(client_socket, client_addr,)).start()