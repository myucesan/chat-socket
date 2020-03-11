import socket
import sys
from protocol import Protocol 
from commands import Command
from time import sleep, time
from threading import Thread
import sys
import copy

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
    
    RETRANSMISSION_TIME = 0.05

    def __init__(self, host="192.168.0.102", port=5382):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = (host, port)
        self.msg_received_list = dict()
        self.msg_send_list = dict() # Keeping track of window
        self._retransmission_list = dict()
        self.name = None
        self.last_delivery = None
        Thread(target=self._clean_msg_lists).start()
        Thread(target=self._retransmit_msgs).start()

    def _clean_msg_lists(self):
        """ Clean list every 10 minutes so it doesnt get oversized """
        while True:
            sleep(6000)
            now = time()
            for key in self.msg_received_list.keys():
                if (now - self.msg_received_list[key]["receiveTime"]) > 9:
                    self.msg_received_list.pop(key)

    def send(self, message, dest_name=None, client_transmission=False, acknowledgement=False, info=None):
        message_to_send = ""
        if client_transmission:
            _name = self._encode_string(self.name)
            _message = self._encode_string(message)
            
            try:
                if self.msg_send_list[dest_name]["window"]["seqNumber"]+1 > MAX_WINDOW_NUMBER:
                    self.msg_send_list[dest_name]["window"]["seqNumber"] = 0
                    if self.msg_send_list[dest_name]["window"]["currentWindow"] == "A":
                        self.msg_send_list[dest_name]["window"]["currentWindow"] = "B"
                    else:
                        self.msg_send_list[dest_name]["window"]["currentWindow"] = "A"
                else:
                    self.msg_send_list[dest_name]["window"]["seqNumber"] = self.msg_send_list[dest_name]["window"]["seqNumber"] + 1 # Increment
                _packet_details = self._encode_string(self.msg_send_list[dest_name]["window"]["currentWindow"] + str(self.msg_send_list[dest_name]["window"]["seqNumber"]))
                message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + MESSAGE + _message + NEW_PACKET + _packet_details + NEW_LINE
            except KeyError:
                self.msg_send_list.update({
                    dest_name: {
                    "receiveTime": time(),
                    "window": {
                        "currentWindow": "A",
                        "seqNumber": 0
                    }
                    }
                    })
                _packet_details = self._encode_string(self.msg_send_list[dest_name]["window"]["currentWindow"] + str(self.msg_send_list[dest_name]["window"]["seqNumber"]))
                message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + MESSAGE + _message + INITIALIZE + _packet_details + NEW_LINE
            self._retransmission_list.update ({
                dest_name: {
                self.msg_send_list[dest_name]["window"]["currentWindow"] + str(self.msg_send_list[dest_name]["window"]["seqNumber"]): {
                    "ackExpected": True, # Initial value
                    "requestToRetransmit": message_to_send, # Initial value
                    "message": message
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
            print(data)
            try:
                if data.decode()[0].isalpha() and data.decode()[-1] == "\n": # Quick check if data is corrupted or not
                    message = data.decode()[:-1] # Remove new line
                    if message.startswith(Protocol.delivery.value):
                        self._process_delivery_string(message) # Method to handle known string
                        return None
                    return [message] 
                else: 
                    return None
            except UnicodeDecodeError:
                print("CORRUPT")
               

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
        if message_["label"] == INITIALIZE or message_["label"] == NEW_PACKET:

            window_cat = message_[message_["label"]][0]
            seq_number =int(message_[message_["label"]][1])
            message = message_[MESSAGE]
            name = message_[NAME]


            self.send("", dest_name=message_[NAME], acknowledgement=True, info=message_[message_["label"]])

            try:
                if (seq_number, message) in self.msg_received_list[name]["window"]["window" + window_cat]["buffer"]:
                    return None
                if self.msg_received_list[name]["window"]["window" + window_cat]["lastSeqNumber"] == seq_number:
                    return None
            except KeyError: # Does not exist at all. Let it initialize..
                pass

            if message_["label"] == INITIALIZE:
                self.msg_received_list.update({
                    name: {
                    "receiveTime": time(),
                    "window": {
                        "currentWindow": window_cat, 
                        "windowA": {
                            "expectedSeqNumber": 0,                       
                            "lastSeqNumber": -1,
                            "buffer": list()
                        },
                        "windowB": {
                            "expectedSeqNumber": 0,
                            "lastSeqNumber": -1,
                            "buffer": list()
                        }
                    }
                    }
                    })
            


            self.msg_received_list[name]["receiveTime"] = time()
            self.msg_received_list[name]["window"]["window" + window_cat]["lastSeqNumber"] = seq_number     
            self.msg_received_list[name]["window"]["window" + window_cat]["buffer"].append((
                seq_number,
                message
            )
            )
            if self.msg_received_list[name]["window"]["window" + window_cat]["expectedSeqNumber"] == seq_number:
                if self.msg_received_list[name]["window"]["currentWindow"] == window_cat:
                    buffer = list()
                    copy_buffer = list() # Used to check how much can be taken from window
                    self.msg_received_list[name]["window"]["window" + window_cat]["buffer"].sort(key=lambda tup: tup[0])
                    seq_expected = 0
                    for data in self.msg_received_list[name]["window"]["window" + window_cat]["buffer"]:
                        copy_buffer.append(data)

                    for idx, message in enumerate(copy_buffer):
                        if idx > 0:
                            if message[0] - self.msg_received_list[name]["window"]["window" + window_cat]["buffer"][idx-1][0] > 1:
                                break
                        self.msg_received_list[name]["window"]["window" + window_cat]["buffer"].pop(idx)
                        buffer.append(message[1])
                        seq_expected = message[0] + 1

                    if seq_expected > MAX_WINDOW_NUMBER:
                        if window_cat == "A":
                            self.msg_received_list[name]["window"]["currentWindow"] = "B"
                        else:
                            self.msg_received_list[name]["window"]["currentWindow"] = "A"

                        if self.msg_received_list[name]["window"]["window" + 
                        self.msg_received_list[name]["window"]["currentWindow"]]["buffer"]:
                            self.msg_received_list[name]["window"]["window" + 
                        self.msg_received_list[name]["window"]["currentWindow"]]["buffer"].sort(key=lambda tup: tup[0])
                            if self.msg_received_list[name]["window"]["window" + 
                            self.msg_received_list[name]["window"]["currentWindow"]]["buffer"][0][0] == 0: # Beginning seq number is 0..
                                copy_buffer = list()
                                for data in self.msg_received_list[name]["window"]["window" + 
                                self.msg_received_list[name]["window"]["currentWindow"]]["buffer"]:
                                    copy_buffer.append(data)
                                for data in copy_buffer:
                                    if idx > 0:
                                        if message[0] - self.msg_received_list[name]["window"]["window" + 
                                        self.msg_received_list[name]["window"]["currentWindow"]]["buffer"][idx-1][0] > 1:
                                            break
                                    buffer.append(message[1])
                                    seq_expected = message[0] + 1
                        else:
                            seq_expected = 0

                    self.msg_received_list[name]["window"]["window" + 
                    self.msg_received_list[name]["window"]["currentWindow"]]["expectedSeqNumber"] = seq_expected
                    for message in buffer:
                        print("Message from: " + name) # Gets username
                        print("Contents: " + message) # Gets message                     
                else:
                    return None
            
        if message_["label"] == ACKNOWLEDGEMENT:
            try:
            
                self._retransmission_list[message_[NAME]][message_[ACKNOWLEDGEMENT]]["ackExpected"] = False
                return None
            except KeyError: # Simply means it no longer exists. Just discard.
                pass

            

    def _retransmit_msgs(self):
        sleep(self.RETRANSMISSION_TIME * 2)
        while True:
            copy_buffer = copy.deepcopy(self._retransmission_list)
            
            for retransmission_name in copy_buffer.keys():
                if not retransmission_name:
                    self._retransmission_list.pop(retransmission_name)
                else:
                    for retransmission in copy_buffer[retransmission_name].keys():
                            if self._retransmission_list[retransmission_name][retransmission]["ackExpected"]:
                                self.send(copy_buffer[retransmission_name][retransmission]["requestToRetransmit"])
                            else:
                                print("You sent a message to " + retransmission_name + ": " + self._retransmission_list[retransmission_name][retransmission]["message"])
                                self._retransmission_list[retransmission_name].pop(retransmission)
                               

            sleep(self.RETRANSMISSION_TIME)

    def set_name(self, name):
        self.name = name

    def close(self):
        self.socket.close()
        
