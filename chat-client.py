import socket # import socket library
import time
from enum import Enum
import threading

class Command (Enum):
    firstHandShake = 'HELLO-FROM '
    secondHandshake = 'HELLO '
    who = 'WHO\n'
    inUse = 'IN-USE\n'
    send = 'SEND '
    sendOk = 'SEND-OK\n'
    unkown = 'UNKNOWN\n'

def receiver():
    while(True):
        receivedMessage = s.recv(2024).decode()
        
        indiceOne = receivedMessage.find(" ")
        indiceTwo = receivedMessage.find(" ", indiceOne + 1)
        if(receivedMessage[0:indiceOne] == "DELIVERY"):
            username = receivedMessage[indiceOne:indiceTwo] # getting username
            message = receivedMessage[indiceTwo:] # getting message
            print("Message from: " + username)
            print("Contents:" + message)
print("Hello there! What is your name?: ")
username = input()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("18.195.107.195", 5378))
message = Command.firstHandShake.value.encode()
username = username.encode()
endOfMessage = b'\n'
num_bytes_sent = s.send(message + username + endOfMessage)

buffer = s.recv(num_bytes_sent)
while (buffer == Command.inUse.value.encode()):
    print("Username is already taken, the server killed the connection so we reconnect...")
    s.close()
    time.sleep(3)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("18.195.107.195", 5378))
    username = input("Please enter a new username: ").encode()
    num_bytes_sent = s.send(message + username + endOfMessage)
    buffer = s.recv(num_bytes_sent)
    print(buffer)


if (buffer == (Command.secondHandshake.value.encode() + username + endOfMessage)):
    receiveMessage = threading.Thread(target=receiver)
    receiveMessage.start()
    # receiveMessage.join(10)
    while(True):
        instruct = input("What do you want to do? (type !quit to exit, type !who to see logged in users, to send a message @username message): \n")
        if (instruct == "!quit"):
            break
        elif (instruct == "!who"):
            num_bytes_sent = s.send(Command.who.value.encode())
            buffer = s.recv(2024).decode()
            usersOnline = buffer[6:].split(",")
            for user in usersOnline:
                print(user)
        elif (instruct[0:1] == '@'):
            # receivingUsername
            indice = instruct.index(" ")
            username = instruct[1:indice] # getting username
            message = instruct[indice:] # getting message
            print("Sending message to " + username)
            print("Message contents: " + message)
            num_bytes_sent = s.send(Command.send.value.encode() + username.encode() + message.encode() +endOfMessage)
            print(Command.send.value.encode() + username.encode() + message.encode())
            buffer = s.recv(num_bytes_sent)

            if (buffer == Command.sendOk.value.encode()):
                print("Message has been sent")
            elif (buffer == Command.unkown.value.encode()):
                print("Destination user is not logged in.")
            
            print(buffer)
        else:
            print("Instruction is unknown.")
else:
    print("Either the maximum amount of client connections have been reached or the server is offline.")

#5. Send messages to other users by typing @username message.
# 6. Receive messages from other users and display them to the user.


s.close()