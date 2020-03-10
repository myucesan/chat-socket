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

    def send(self, message, client_transmission=False):
        message = message + NEW_LINE
        self.socket.sendto(message.encode(), self.server)

    def receive(self):
        message = ""
        full_message = ""
        details = ""
        counter = 0
        skip = False
        while True:
            data, addr = self.socket.recvfrom(4096)
            return [data.decode()]

    def _decode_valid_bytes(data):
        pass

    def _retransmit_timer(self):
        sleep(self.RETRANSMISSION_TIME * 2)
        while self._retransmission_list["ackExpected"]:
            self.send(self._retransmission_list["requestToRetransmit"])
            sleep(self.RETRANSMISSION_TIME)

    def close(self):
        self.socket.close()
        
