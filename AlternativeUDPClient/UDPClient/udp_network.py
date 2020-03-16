import socket
import sys
from protocol import Protocol 
from commands import Command
from time import sleep, time
from threading import Thread
import sys
import copy
import crc_help
NEW_LINE = "\n"
MAX_WINDOW_NUMBER = 7
INITIAL_SEQUENCE = "0A"

# States
ESCAPE = "/"
MESSAGE = "M"
NAME = "N"
INITIALIZE = "I"
NEW_PACKET = "P"
ACKNOWLEDGEMENT = "A"

class UdpNetwork:
    
    RETRANSMISSION_TIME = 0.01

    def __init__(self, host="18.195.107.195", port=5382):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = (host, port)
        self.msg_received_list = dict()
        self.msg_send_list = dict() # Keeping track of window
        self.name = None
        self.last_delivery = None
        self.send_counter = 0
        self.last_unknown_msg_time = None
        self.last_unknown_msg_name = None
        Thread(target=self._clean_msg_lists).start()
        Thread(target=self._retransmit_msgs).start()

    def _clean_msg_lists(self):
        """ Clean list every 10 minutes so it doesnt get oversized """
        while True:
            sleep(6000)
            now = time()
            copy_buffer = copy.deepcopy(self.msg_received_list)
            for key in copy_buffer.keys():
                if (now - self.msg_received_list[key]["receiveTime"]) > 9*60:
                    self.msg_received_list.pop(key)
            copy_buffer = copy.deepcopy(self.msg_send_list)
            for key in copy_buffer.keys():
                if (now - self.msg_send_list[key]["receiveTime"]) > 9*60:
                    self.msg_received_list.pop(key)

    def send(self, message, dest_name=None, resend=False, client_transmission=False, acknowledgement=False, info=None):
        message_to_send = ""
        
        if client_transmission:
            _name = self._encode_string(self.name)
            _message = self._encode_string(message)
            
            try:
                
                _packet_details = self._encode_string(self.msg_send_list[dest_name]["window"] + str(self.msg_send_list[dest_name]["seqNumber"]))
                message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + MESSAGE + _message + NEW_PACKET + _packet_details 
                mock_receive_msg = Protocol.delivery.value + " " + self.name + " " + NAME + _name + MESSAGE + _message + NEW_PACKET + _packet_details 
                self.socket.sendto(message_to_send.encode() + crc_help.convert_crc(mock_receive_msg) + NEW_LINE.encode(), self.server)
                self.last_unknown_msg_name = dest_name
                self.last_unknown_msg_time = time()
                self.send_counter = 0
            except KeyError:
                self.msg_send_list.update({
                    dest_name: {
                    "receiveTime": time(),
                    "window": "A",
                    "seqNumber": 0,
                    "buffer": dict()
                    }
                    })

                _packet_details = self._encode_string(self.msg_send_list[dest_name]["window"] + str(self.msg_send_list[dest_name]["seqNumber"]))
                message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + MESSAGE + _message + INITIALIZE + _packet_details 
                mock_receive_msg = Protocol.delivery.value + " " + self.name + " " + NAME + _name + MESSAGE + _message + INITIALIZE + _packet_details
                self.socket.sendto(message_to_send.encode() + crc_help.convert_crc(mock_receive_msg) + NEW_LINE.encode(), self.server)
                self.last_unknown_msg_name = dest_name
                self.last_unknown_msg_time = time()
                self.send_counter = 0
            self.msg_send_list[dest_name]["buffer"].update(
                {self.msg_send_list[dest_name]["window"] + str(self.msg_send_list[dest_name]["seqNumber"]):
                {
                    "ackExpected": True, # Initial value
                    "requestToRetransmit": message_to_send.encode() + crc_help.convert_crc(mock_receive_msg) + NEW_LINE.encode(), # Initial value
                    "message": message                    
                }})

            self.msg_send_list[dest_name]["seqNumber"] = self.msg_send_list[dest_name]["seqNumber"] + 1
            if self.msg_send_list[dest_name]["seqNumber"] > MAX_WINDOW_NUMBER:
                if self.msg_send_list[dest_name]["window"] == "A":
                    self.msg_send_list[dest_name]["window"] = "B"
                    
                else:
                    self.msg_send_list[dest_name]["window"] = "A"
                self.msg_send_list[dest_name]["seqNumber"] = 0

        elif acknowledgement:
            _name = self._encode_string(self.name)
            _info = self._encode_string(info)
            _dest_name = self._encode_string(dest_name)
            message_to_send = Protocol.request_send.value + " " + dest_name + " " + NAME + _name + ACKNOWLEDGEMENT + _info  # Window en sequence number
            mock_receive_msg = Protocol.delivery.value + " " + self.name + " " + NAME + _name + ACKNOWLEDGEMENT + _info
            self.socket.sendto(message_to_send.encode() + crc_help.convert_crc(mock_receive_msg) + NEW_LINE.encode(), self.server)
            self.last_unknown_msg_name = dest_name
            self.last_unknown_msg_time = time()
            self.send_counter = 0

        elif resend:
            self.socket.sendto(message, self.server)
        else:
            message_to_send = message + NEW_LINE
            self.socket.sendto(message_to_send.encode(), self.server)



    def receive(self):
        while True:
            data, addr = self.socket.recvfrom(4096)
            try:
                if data.decode()[0].isalpha() and data.decode()[-1] == "\n": # Quick check if data is corrupted or not
                    message = data.decode()[:-1] # Remove new line
                    if message.startswith(Protocol.delivery.value):
                        self._process_delivery_string(data[:-1]) # Method to handle in bytes cause of crc
                        return None
                    if message.startswith(Protocol.unknown.value):
                        if time() - self.last_unknown_msg_time < self.RETRANSMISSION_TIME*15:
                            self.send_counter = self.send_counter + 1
                            if self.send_counter >= 2:
                                try:
                                    self.msg_send_list.pop(self.last_unknown_msg_name)
                                except: # Mary already have been removed. Ignore.
                                    pass
                                return None
                    return [message] 
                else:
                    self._process_delivery_string(data[:-1])
                    return None
            except UnicodeDecodeError: # Data corrupted? Confirm with CRC for delivery
                self._process_delivery_string(data[:-1])
               

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
        result = crc_help.detect_crc(message)
        if not result[0]:
            print("CRC CHECK FAILED - INVALID DATA")
            return None # Data corrupted. Discard.
        message = result[1] # Passed CRC. Lets handle it.
        message_ = self._decode_string(message.split(" ", 1)[1].split(" ", 1)[1])
        if message_["label"] == INITIALIZE or message_["label"] == NEW_PACKET:

            window_cat = message_[message_["label"]][0]
            seq_number = int(message_[message_["label"]][1])
            message = message_[MESSAGE]
            name = message_[NAME]

            try:
                if self.msg_received_list[name]["lastSeqNumber"] == message_[message_["label"]]:
                    return None
            except KeyError: # Does not exist at all. Let it initialize..
                pass

            if message_["label"] == INITIALIZE:
                expected_seq = "A1"
                self.msg_received_list.update({
                    name: {
                    "receiveTime": time(),
                    "expectedSeqNumber": message_[message_["label"]],
                    "lastSeqNumber": None
                    }
                    })
            


            self.msg_received_list[name]["receiveTime"] = time()
            if self.msg_received_list[name]["expectedSeqNumber"] != message_[message_["label"]]:
                return None
            else:
                self.send("", dest_name=message_[NAME], acknowledgement=True, info=message_[message_["label"]])
                self.msg_received_list[name]["lastSeqNumber"] = self.msg_received_list[name]["expectedSeqNumber"]
                new_seq_number = seq_number + 1

                if new_seq_number > MAX_WINDOW_NUMBER:
                    if window_cat == "A":
                        window_cat = "B"
                    else:
                        window_cat = "A"
                    self.msg_received_list[name]["expectedSeqNumber"] = window_cat + "0"
                else:
                    self.msg_received_list[name]["expectedSeqNumber"] = window_cat + str(new_seq_number)
                
                print("Message from: " + name) # Gets username
                print("Contents: " + message)
            return None 
            
        if message_["label"] == ACKNOWLEDGEMENT:
            try:
            
                self.msg_send_list[message_[NAME]]["buffer"][message_[ACKNOWLEDGEMENT]]["ackExpected"] = False
                return None
            except KeyError: # Simply means it no longer exists. Just discard.
                pass

            

    def _retransmit_msgs(self):
        sleep(self.RETRANSMISSION_TIME * 2)
        while True:
            copy_buffer = copy.deepcopy(self.msg_send_list)
            
            for retransmission_name in copy_buffer.keys():
                for retransmission in copy_buffer[retransmission_name]["buffer"].keys():
                    try:
                        if self.msg_send_list[retransmission_name]["buffer"][retransmission]["ackExpected"]:
                            self.send(copy_buffer[retransmission_name]["buffer"][retransmission]["requestToRetransmit"], resend=True)
                        else:
                            print("You sent a message to " + retransmission_name + ": " + self.msg_send_list[retransmission_name]["buffer"][retransmission]["message"])
                            self.msg_send_list[retransmission_name]["buffer"].pop(retransmission)
                    except KeyError:
                        pass # Removed so ignore.
                               

            sleep(self.RETRANSMISSION_TIME)

    def set_name(self, name):
        self.name = name

    def close(self):
        self.socket.close()
        
