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
        self._retransmission_list = dict()
        self.name = None
        self.last_delivery = None
        #Thread(target=self._clean_msg_lists).start()
        Thread(target=self._retransmit_msgs).start()

    def send(self, message, dest_name=None, client_transmission=False, acknowledgement=False, info=None):
        message_to_send = ""
        if client_transmission:
            _name = self._encode_string(self.name)
            _message = self._encode_string(message)
            
            try:
                if self.msg_send_list[self.name]["window"]["seqNumber"]+1 > MAX_WINDOW_NUMBER:
                    self.msg_send_list[self.name]["window"]["seqNumber"] = 0
                    if self.msg_send_list[self.name]["window"]["currentWindow"] == "A":
                        self.msg_send_list[self.name]["window"]["currentWindow"] = "B"
                    else:
                        self.msg_send_list[self.name]["window"]["currentWindow"] = "A"
                else:
                    self.msg_send_list[self.name]["window"]["seqNumber"] = self.msg_send_list[self.name]["window"]["seqNumber"] + 1 # Increment
                _packet_details = self._encode_string(self.msg_send_list[self.name]["window"]["currentWindow"] + str(self.msg_send_list[self.name]["window"]["seqNumber"]))
                message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + MESSAGE + _message + NEW_PACKET + _packet_details + NEW_LINE
            except KeyError:
                self.msg_send_list.update({
                    self.name: {
                    "receiveTime": time(),
                    "window": {
                        "currentWindow": "A",
                        "seqNumber": 0
                    }
                    }
                    })
                _packet_details = self._encode_string(self.msg_send_list[self.name]["window"]["currentWindow"] + str(self.msg_send_list[self.name]["window"]["seqNumber"]))
                message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + MESSAGE + _message + INITIALIZE + _packet_details + NEW_LINE
            self._retransmission_list.update ({
                dest_name: {
                self.msg_send_list[self.name]["window"]["currentWindow"] + str(self.msg_send_list[self.name]["window"]["seqNumber"]): {
                    "ackExpected": True, # Initial value
                    "requestToRetransmit": message_to_send # Initial value
            }}})

        elif acknowledgement:
            _name = self._encode_string(self.name)
            _info = self._encode_string(info)
            _dest_name = self._encode_string(dest_name)
            message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + ACKNOWLEDGEMENT + _info + NEW_LINE # Window en sequence number
        else:
            message_to_send = message + NEW_LINE
        self.socket.sendto(message_to_send.encode(), self.server)

    def receive(self):
        while True:
            data, addr = self.socket.recvfrom(4096)
            if data.decode()[0].isalpha() and data.decode()[-1] == "\n": # Quick check if data is corrupted or not
                message = data.decode()[:-1] # Remove new line
                if message.startswith(Protocol.delivery.value):
                    self._process_delivery_string(message) # Method to handle known string
                return [message] # return [message] doet die het maar opvolgende error even fixen
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
            "label": ""
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
                    message_list["label"] = ACKNOWLEDGEMENT
                    state = ACKNOWLEDGEMENT
                elif character ==  NEW_PACKET:
                    message_list["label"] = NEW_PACKET
                    state = NEW_PACKET
                elif character == INITIALIZE:
                    message_list["label"] = INITIALIZE
                    state = INITIALIZE
                else:
                    message_list[state] += character
            else:
                skip = False
                message_list[state] += character
        return message_list

    def _process_delivery_string(self, message):
        message_ = self._decode_string(message.split(" ", 1)[1].split(" ", 1)[1])
        print(message_)
        if message_["label"] == INITIALIZE:
            self.send("", dest_name=message_[NAME], acknowledgement=True, info=message_[INITIALIZE])
            #Discard Duplicates
            #Handle order

        if message_["label"] == NEW_PACKET:
            self.send("", dest_name=message_[NAME], acknowledgement=True, info=message_[NEW_PACKET])
            #Discard Duplicates
            #Handle order
            
        if message_["label"] == ACKNOWLEDGEMENT:
            try:
                self._retransmission_list[message_[NAME]][message_[ACKNOWLEDGEMENT]]["ackExpected"] = False
            except KeyError: # Simply means it no longer exists. Just discard.
                return None

            

    def _retransmit_msgs(self):
        sleep(self.RETRANSMISSION_TIME * 2)
        while True:
            for retransmission_name in self._retransmission_list.keys():
                if not retransmission_name:
                    self._retransmission_list.pop(retransmission_name)
                else:
                    for retransmission in self._retransmission_list[retransmission_name].keys():
                            if self._retransmission_list[retransmission_name][retransmission]["ackExpected"]:
                                self.send(self._retransmission_list[retransmission_name][retransmission]["requestToRetransmit"])
                            else:
                                self._retransmission_list[retransmission_name].pop(retransmission)
                    
            sleep(self.RETRANSMISSION_TIME)

    def set_name(self, name):
        self.name = name

    def close(self):
        self.socket.close()
        
