import socket
import sys
from protocol import Protocol 
from commands import Command
from time import sleep, time
from threading import Thread
import sys

NEW_LINE = "\n"
MAX_WINDOW_NUMBER = 7

# States
ESCAPE = "/"
MESSAGE = "M"
NAME = "N"
INITIALIZE = "I"
NEW_PACKET = "P"
ACKNOWLEDGEMENT = "A"

class UdpNetwork:
    
    RETRANSMISSION_TIME = 0.04

    def __init__(self, host="18.195.107.195", port=5382):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = (host, port)
        self.msg_received_list = dict()
        self.msg_send_list = dict()
        self._retransmission_list = {
            "ackExpected": False, # Initial value
            "requestToRetransmit": None, # Initial value
        }

        self.last_delivery = None
        #Thread(target=self._clean_msg_lists).start()

    def send(self, message, dest_name=None, name=None, client_transmission=False, acknowledgement=False):
        print("I have just entered the send() function.")
        message_to_send = ""
        if client_transmission:
            print("Client transmission")
            message_to_send = Protocol.request_send.value + " " + dest_name + " " + message + NEW_LINE
            # try:
            #     message = Protocol.request_send.value + " " + dest_name + " " + NAME + name + MESSAGE + message + NEW_PACKET + "A1" + NEW_LINE # Window en sequence number
            # except KeyError:
            #     message = Protocol.request_send.value + " " + dest_name + " " + NAME + name + MESSAGE + message + INITIALIZE + "A1" + NEW_LINE # Window en sequence number
            # print(message)
            # print("Generated message ^")  
            # message = Protocol.request_send.value + " " + dest_name + " " + "test\n"  

        elif acknowledgement:
            message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + name + ACKNOWLEDGEMENT + "A1" + NEW_LINE # Window en sequence number
        else:
            message_to_send = message + NEW_LINE
        print(message_to_send)
        self.socket.sendto(message_to_send.encode(), self.server)

    def receive(self):
        print("I have just entered the receive.")
        while True:
            data, addr = self.socket.recvfrom(4096)
            # print(data)
            if data.decode()[0].isalpha() and data.decode()[-1] == "\n": # Quick check if data is corrupted or not
                message = data.decode()[:-1] # Remove new line
                if message.startswith(Protocol.delivery.value):
                    print("INVOKED")
                    self._process_delivery_string(message) # Method to handle known string
                return message # return [message] doet die het maar opvolgende error even fixen
            else:
                pass

    def _encode_string(self, message): # Encode with escape bytes, so that information can be sent to client UDP
        new_message = ""
        for letter in message:
            if letter == MESSAGE or letter == ACKNOWLEDGEMENT or letter == INITIALIZE or letter == NEW_PACKET or letter == NAME:
                new_message += ESCAPE + letter # Adds escape
            else:
                new_message += letter
        return new_message

    def _decode_string(self, data): # Decode received message and split the information in a dict

        message_list = {
            NAME: "",
            MESSAGE: "",
            ACKNOWLEDGEMENT: "",
            INITIALIZE: "",
            NEW_PACKET: "",
            "Label": ""
        }

        state = None
        skip = False
        for idx, character in enumerate(data):
            
            if not skip:
                if character == ESCAPE:
                    if data[idx+1] == NAME or data[idx+1] == MESSAGE or data[idx+1] == ACKNOWLEDGEMENT or data[idx+1] == INITIALIZE or data[idx+1] == NEW_PACKET:
                        skip = True
                        continue
                elif character ==  NAME:
                    state = NAME
                elif character == MESSAGE:
                    state = MESSAGE
                elif character == ACKNOWLEDGEMENT:
                    message_list["Label"] = ACKNOWLEDGEMENT
                    state = ACKNOWLEDGEMENT
                elif character ==  NEW_PACKET:
                    message_list["Label"] = NEW_PACKET
                    state = NEW_PACKET
                elif character == INITIALIZE:
                    message_list["Label"] = INITIALIZE
                    state = INITIALIZE
                else:
                    message_list[state] += character
            else:
                skip = False
                message_list[state] += character
        return message_list

    def _process_delivery_string(self, message):
        message_ = message[1].split(" ", 1)[1]
        print(message_)

    def _retransmit_timer(self):
        sleep(self.RETRANSMISSION_TIME * 2)
        while self._retransmission_list["ackExpected"]:
            self.send(self._retransmission_list["requestToRetransmit"])
            sleep(self.RETRANSMISSION_TIME)

    def close(self):
        self.socket.close()
        
