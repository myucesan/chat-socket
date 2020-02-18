"""
    client.py

    The main application of this assignment. In this application, the client connects to a server
    where it can contact other clients and send messages. The server details are hidden in constants.py
    and the primitives used to communicate with the server are hidden in protocol.py. The socket library 
    is used to connect to the server through TCP.

"""

import socket
import threading
import constants
from protocol import Protocol
import time

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Define the client from beginning so it can be accessed by other files
allow_receiving = False # Used to allow the server_process method to start receiving after user has given a valid name
username = None
dest_name = None
last_inserted_msg = None

def receive_response():
    response_text = ""
    while True:
        response  = client.recv(1).decode()
        if response == "\n":
            return response_text
        response_text += response


def client_process():
    """
        client_process

        This thread handles user requests and transmits information to the server.
        Before allowing the user to use various commands, the user has to send a valid name before 
        he/she can do something on the server. That is also before the server process
        gets to do something.   
    """
    global allow_receiving
    global client
    global username
    global last_inserted_msg
    global dest_name
    print("Hello there! What is your name?: ")
    # Ensure that a valid and available username is taken
    while username is None:
        username = input()
        if " " in username or username is None:
            username = None
            print("Your inserted username is invalid! Please insert another username: ")
        else:
            request = Protocol.request_handshake.value + " " + username + "\n"
            client.sendall(request.encode())
            response = receive_response()
            if response.startswith(Protocol.in_use.value):
                username = None
                # the server killed the connection so we reconnect...
                client.close()
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((constants.HOST, constants.PORT))
                print("Username is already taken, please insert another username: ")
            elif response.startswith(Protocol.busy.value):
                print("Sorry, but you cannot login right now, as the maximum number of clients has been reached. Try again later!")
                time.sleep(10)
                print("Hello there! What is your name?: ")
            elif response.startswith(Protocol.response_handshake.value):
                print("Welcome " + str(username) + "! What would you like to do? Please write !help to see the commands.")
                allow_receiving = True
    while True:
        command = input()
        if command.startswith("!help"):
            print("The following commands are available: ")
            print("!help                - Prints the available commands")
            print("!who                 - List all currently logged-in users. Can only be used after you succesfully connect to the server!")
            print("!quit                - Shut down the client")
            print("@username <message>  - Send a message to an user in the server. Can only be used after you succesfully connect to the server!")

        elif command.startswith("!who"):
            request = Protocol.request_who.value + "\n"
            client.sendall(request.encode())
        elif command.startswith("@"):
            details = command[1:].split(" ", 1)
            dest_name = details[0]
            last_inserted_msg = details[1]
            request = Protocol.request_send.value + " " + dest_name + " " + last_inserted_msg + "\n"
            client.sendall(request.encode())
        elif command.startswith("!quit"):
            client.close()
            break
        else:
            print("Unknown command. Please access !help to learn about the available commands.")





def server_process():
    """ Receives incoming messages from the server and processes them accordingly """
    global allow_receiving
    global dest_name
    global last_inserted_msg
    while True:
            if allow_receiving:
                try:
                    response = receive_response()
                    if response is not None:
                        if response.startswith(Protocol.response_who.value):
                            online_users = response.split(Protocol.response_who.value + " ", 1)[1].rstrip("\n").split(",")
                            print("The online users in the network are: ")
                            for user in online_users:
                                print(user)
                        if response.startswith(Protocol.response_send.value):
                            print("You sent a message to " + dest_name + ": " + last_inserted_msg)
                        if response.startswith(Protocol.bad_request_header.value):
                            print("Your message contains an error in the header. Please resend")
                        if response.startswith(Protocol.bad_request_body.value):
                            print("Your message contains an error in the body. Please resend")
                        if response.startswith(Protocol.unknown.value):
                            print("The user you sent the message to does not exist.")
                        if response.startswith(Protocol.delivery.value):
                            received = response.split(" ", 1)[1].split(" ", 1)
                            print("Message from: " + received[0]) # Gets username
                            print("Contents: " + received[1]) # Gets message
                except ConnectionAbortedError:
                    print("Goodbye.")
                    break




if __name__ == '__main__':
    print("Starting the client...")
    print("Connecting to the server...")
    client.connect((constants.HOST, constants.PORT))
    thread_req = threading.Thread(target=client_process)
    thread_resp = threading.Thread(target=server_process)
    thread_req.start()
    thread_resp.start()
    thread_req.join()
    thread_resp.join()

