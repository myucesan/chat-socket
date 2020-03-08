""" 
    protocol.py

    This class is used as a protocol interface, and contains all the messages 
    being sent back and forth between the client and the server. Appendix A
    in the Lab Guide can be accessed to find the meaning of each protocol
    message. 
"""
from enum import Enum

class Protocol(Enum):

    request_handshake = "HELLO-FROM"
    response_handshake = "HELLO"
    request_who = "WHO"
    response_who = "WHO-OK"
    request_send = "SEND"
    response_send = "SEND-OK"
    unknown = "UNKNOWN"
    delivery = "DELIVERY"
    in_use = "IN-USE"
    busy = "BUSY"
    bad_request_header = "BAD-RQST-HDR"
    bad_request_body = "BAD-RQST-BODY"