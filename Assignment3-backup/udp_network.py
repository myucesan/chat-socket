import socket
import sys
from protocol import Protocol 
from commands import Command
from time import sleep, time
from threading import Thread
import sys

NEW_LINE = "\n"

class UdpNetwork:
    
    RETRANSMISSION_TIME = 0.02

    def __init__(self, host="18.195.107.195", port=5382):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = (host, port)
        self.msg_received_list = dict()
        self.msg_sent_list = dict()
        # Checks based on ackExpected what it is going to retransmit
        self._retransmission_list = {
            "ackExpected": 0, # Initial value
            "requestToRetransmit": None, # Initial value
        }
        Thread(target=self._clean_msg_lists).start()

    def _clean_msg_lists(self):
        """ Clean list every 5 sec so it doesnt get oversized """
        while True:
            sleep(10)
            now = time()
            for key in self.msg_sent_list.keys():
                if (self.msg_sent_list[key]["transmitTime"] - now) > 5:
                    self.msg_sent_list.pop(key)
            for key in self.msg_received_list.keys():
                if (self.msg_received_list[key]["receiveTime"] - now) > 5:
                    self.msg_received_list.pop(key)



    def receive(self):
        message = ""
        test = ""
        while True:
            data, addr = self.socket.recvfrom(1024)
            if addr == self.server:
                for byte in data:            
                    if chr(byte) == "\n":
                        if message.startswith(Protocol.delivery.value):
                            received = message.split(" ", 1)
                            received = received[1].split(" ", 1)
                            try:
                                if self.msg_received_list[received[0]]["seqNumber"] == received[1][-1]:
                                    return None
                                self.msg_received_list[received[0]]["seqNumber"] = received[1][-1]
                            except KeyError:
                                self.msg_received_list[received[0]] = {
                                    "seqNumber": received[1][-1],
                                    "receiveTime": time()
                                }
                                self.msg_received_list[received[0]]["seqNumber"] = received[1][-1]
                            return message
                        else:
                            if self._retransmission_list["ackExpected"] == 1:
                                self._retransmission_list["ackExpected"] = 0 # That means theres a response from the last time client sent something
                                return message
                        return None
                    message += chr(byte)

    def send(self, message, delivery=False, name=None):
        message_to_send = None
        if delivery:
            try:
                self.msg_sent_list[name]["seqNumber"] = self.msg_sent_list[name]["seqNumber"] ^ 1
                self.msg_sent_list[name]["transmitTime"] = time()
            except KeyError:
                self.msg_sent_list[name] = {
                    "seqNumber": 0,
                    "transmitTime": time()
                }
            print(self.msg_sent_list)
            message_to_send = message + str(self.msg_sent_list[name]["seqNumber"]) +  NEW_LINE
        else:
            message_to_send = message +  NEW_LINE
        self._retransmission_list["ackExpected"] = 1
        self._retransmission_list["requestToRetransmit"] = message_to_send
        self.socket.sendto(message_to_send.encode(), self.server)
        Thread(target=self._retransmit_timer).start()

    def _send(self, message):
        message_to_send = message + NEW_LINE
        self.socket.sendto(message_to_send.encode(), self.server)
        Thread(target=self._retransmit_timer).start()

    def _retransmit_timer(self):
        sleep(self.RETRANSMISSION_TIME)
        while self._retransmission_list["ackExpected"] == 1:
            self._send(self._retransmission_list["requestToRetransmit"])
            sleep(self.RETRANSMISSION_TIME)

    def close(self):
        self.socket.close()
        



