"""
    client.py

    The main application of this assignment. In this application, the client connects to a server
    where it can contact other clients and send messages. The server details are hidden in constants.py
    and the primitives used to communicate with the server are hidden in protocol.py. The socket library 
    is used to connect to the server through TCP.

"""

from udp_network import UdpNetwork
import threading
from protocol import Protocol
from commands import Command
import time
udp_client = UdpNetwork()

allow_receiving = False # Used to allow the server_process method to start receiving after user has given a valid name
username = None
dest_name = None
last_inserted_msg = None

def client_process():
    """
        client_process

        This thread handles user requests and transmits information to the server.
        Before allowing the user to use various commands, the user has to send a valid name before 
        he/she can do something on the server. That is also before the server process
        gets to do something.   
    """
    global allow_receiving
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
            request = Protocol.request_handshake.value + " " + username
            udp_client.send(request)
            response = udp_client.receive()[0]
            response = response.split(" ", 1)
            if response[0] == Protocol.in_use.value:
                username = None
                print("Username is already taken, please insert another username: ")
            elif response[0] == Protocol.busy.value:
                print("Sorry, but you cannot login right now, as the maximum number of clients has been reached. Try again later!")
                time.sleep(10)
                print("Hello there! What is your name?: ")
            elif response[0] == Protocol.response_handshake.value:
                udp_client.set_name(username)
                print("Welcome " + str(username) + "! What would you like to do? Please write !help to see the commands.")
                allow_receiving = True
    while True:
        command = input()
        if command == "!help":
            print("The following commands are available: ")
            print("!help                - Prints the available commands")
            print("!who                 - List all currently logged-in users. Can only be used after you succesfully connect to the server!")
            print("!quit                - Shut down the client")
            print("@username <message>  - Send a message to an user in the server. Can only be used after you succesfully connect to the server!")

        elif command == "!who":
            request = Protocol.request_who.value
            udp_client.send(request)
        elif command.startswith("@"):
            details = command[1:].split(" ", 1)
            dest_name = details[0]
            last_inserted_msg = details[1]
            request = Protocol.request_send.value + " " + dest_name + " " + last_inserted_msg
            udp_client.send(last_inserted_msg, dest_name=dest_name, client_transmission=True)
        elif command.startswith("!debug"):
            details = command.split(" ", 1)
            print(details)
            if details[1].startswith("drop"):
                value = details[1].split(" ", 1)[1]
                request = Command.set_drop.value + " " + value
                udp_client.send(request)                
            if details[1].startswith("flip"):
                value = details[1].split(" ", 1)[1]
                request = Command.set_flip.value + " " + value
                udp_client.send(request)  
            if details[1].startswith("burst"):
                value = details[1].split(" ", 1)[1]
                request = Command.set_burst.value + " " + value
                udp_client.send(request)  
            if details[1].startswith("delay"):
                value = details[1].split(" ", 1)[1]
                request = Command.set_delay.value + " " + value
                udp_client.send(request)  
            if details[1] == "burst-len":
                values = details[1].split(" ", 3)
                request = Command.set_burst_len + " " + values[1] + " " + values[2]
                udp_client.send(request) 
            if details[1].startswith("delay-len"):
                print("Invoked")
                values = details[1].split(" ", 3)
                print("Going...")
                request = Command.set_delay_len.value + " " + values[1] + " " + values[2]
                print(request)
                udp_client.send(request) 
            if details[1] == "reset":
                request = Command.reset.value
                udp_client.send(request)
        elif command == "!quit":
            udp_client.close()
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
                    response_list = udp_client.receive()
                    if response_list is not None:
                        for response in response_list:
                            response = response.split(" ", 1)
                            if response[0] == Protocol.response_who.value:
                                online_users = response[1].split(",")
                                print("The online users in the network are: ")
                                for user in online_users:
                                    print(user)
                            if response[0] == Protocol.bad_request_header.value:
                                print("Your message contains an error in the header. Please resend")
                            if response[0] == Protocol.bad_request_body.value:
                                print("Your message contains an error in the body. Please resend")
                            if response[0] ==  Protocol.unknown.value:
                                print("The user you sent the message to does not exist.")
                except ConnectionAbortedError:
                    print("Goodbye.")
                    break




if __name__ == '__main__':
    print("Starting the client...")
    print("Connecting to the server...")
    thread_req = threading.Thread(target=client_process)
    thread_resp = threading.Thread(target=server_process)
    thread_req.start()
    thread_resp.start()
    thread_req.join()
    thread_resp.join()

