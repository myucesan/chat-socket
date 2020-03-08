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
DETAILS = "D"
INITIALIZE = "I"
ONGOING = "G"
RESEND = "R"
ESCAPE = "/"

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
        Thread(target=self._clean_msg_lists).start()

    def _clean_msg_lists(self):
        """ Clean list every 10 minutes so it doesnt get oversized """
        while True:
            sleep(6000)
            now = time()
            for key in self.msg_received_list.keys():
                if (now - self.msg_received_list[key]["receiveTime"]) > 9:
                    self.msg_received_list.pop(key)

    def receive(self):
        message = ""
        full_message = ""
        details = ""
        counter = 0
        skip = False
        while True:
            data, addr = self.socket.recvfrom(4096)
            for idx, byte in enumerate(data):
                if skip:
                    skip = False
                    continue            
                if chr(byte) == "\n":
                    if message.startswith(Protocol.response_send.value) or message.startswith(Protocol.unknown.value):
                        self._retransmission_list["ackExpected"] = False
                    if message.startswith(Protocol.delivery.value):
                        print(message)
                        print(details)
                        if self.last_delivery is not None:
                            if full_message == self.last_delivery:
                                return None
                        received = message.split(" ", 1)
                        received = received[1].split(" ", 1)
                        if details[0] == INITIALIZE:
                            self.msg_received_list.update({
                                received[0]: {
                                "receiveTime": time(),
                                "window": {
                                    "currentWindow": details[1], 
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
                        
                        rcv_seq = int(details[2:])
                        if self.msg_received_list[received[0]]["window"]["window" + details[1]]["lastSeqNumber"] == rcv_seq:
                            return None
                        self.msg_received_list[received[0]]["receiveTime"] = time()
                        self.msg_received_list[received[0]]["window"]["window" + details[1]]["lastSeqNumber"] = rcv_seq     
                        self.msg_received_list[received[0]]["window"]["window" + details[1]]["buffer"].append((
                            rcv_seq,
                            message
                        )
                        )
                        if self.msg_received_list[received[0]]["window"]["window" + details[1]]["expectedSeqNumber"] == rcv_seq:
                            if self.msg_received_list[received[0]]["window"]["currentWindow"] == details[1]:
                                buffer = list()
                                self.msg_received_list[received[0]]["window"]["window" + details[1]]["buffer"].sort(key=lambda tup: tup[0])
                                highest_seq = self.msg_received_list[received[0]]["window"]["window" + details[1]]["buffer"][-1][0]
                                for message in self.msg_received_list[received[0]]["window"]["window" + details[1]]["buffer"]:
                                    buffer.append(message[1])
                                self.msg_received_list[received[0]]["window"]["window" + details[1]]["buffer"].clear()
                                if rcv_seq == MAX_WINDOW_NUMBER:
                                    if details[1] == "A":
                                        self.msg_received_list[received[0]]["window"]["currentWindow"] = "B"
                                    else:
                                        self.msg_received_list[received[0]]["window"]["currentWindow"] = "A"
                                    self.msg_received_list[received[0]]["window"]["window" + details[1]]["expectedSeqNumber"] = 0
                                else:
                                    self.msg_received_list[received[0]]["window"]["window" + details[1]]["expectedSeqNumber"] = highest_seq + 1
                                return buffer
                            return None
                        else:
                            return None
                    return [message]
                if chr(byte) == "/" and chr(data[idx+1] == "D"):
                    skip = True
                    counter = 1 
                    continue  
                if counter == 0:
                    message += chr(byte)
                else:
                    details += chr(byte)
 
                full_message += chr(byte)

    def send(self, message, client_transmission=False):
        if client_transmission:
            received = message.split(" ", 1)
            received = received[1].split(" ", 1)
            try:
                if self.msg_send_list[received[0]]["window"]["seqNumber"]+1 > MAX_WINDOW_NUMBER:
                    self.msg_send_list[received[0]]["window"]["seqNumber"] = 0
                    if self.msg_send_list[received[0]]["window"]["currentWindow"] == "A":
                        self.msg_send_list[received[0]]["window"]["currentWindow"] = "B"
                    else:
                        self.msg_send_list[received[0]]["window"]["currentWindow"] = "A"
                else:
                    self.msg_send_list[received[0]]["window"]["seqNumber"] = self.msg_send_list[received[0]]["window"]["seqNumber"] + 1 # Increment
                message = message + ESCAPE + DETAILS + ONGOING  + self.msg_send_list[received[0]]["window"]["currentWindow"] + str(self.msg_send_list[received[0]]["window"]["seqNumber"]) + NEW_LINE
            except KeyError:
                self.msg_send_list.update({
                    received[0]: {
                    "receiveTime": time(),
                    "window": {
                        "currentWindow": "A",
                        "seqNumber": 0
                    }
                    }
                    })
                message = message + ESCAPE + DETAILS + INITIALIZE  + self.msg_send_list[received[0]]["window"]["currentWindow"] + str(self.msg_send_list[received[0]]["window"]["seqNumber"]) + NEW_LINE
            print("Sequence number")
            print(self.msg_send_list[received[0]]["window"]["seqNumber"])
            self._retransmission_list["ackExpected"] = True
            self._retransmission_list["requestToRetransmit"] = message
            self.socket.sendto(message.encode(), self.server)
            Thread(target=self._retransmit_timer).start()
            return
        
        message = message + NEW_LINE
        self.socket.sendto(message.encode(), self.server)

    def _retransmit_timer(self):
        sleep(self.RETRANSMISSION_TIME * 2)
        while self._retransmission_list["ackExpected"]:
            self.send(self._retransmission_list["requestToRetransmit"])
            sleep(self.RETRANSMISSION_TIME)

    def close(self):
        self.socket.close()
        



