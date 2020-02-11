""" 
    protocol.py

    This class is used as a protocol interface, and contains all the messages 
    being sent back and forth between the client and the server. Appendix A
    in the Lab Guide can be accessed to find the meaning of each protocol
    message. 
"""
from enum import Enum

class Protocol(Enum):

    request_handshake = "HELLO-FROM <name>\n"
    response_handshake = "HELLO"
    request_who = "WHO\n"
    response_who = "WHO-OK"
    request_send = "SEND <user> <msg>\n"
    response_send = "SEND-OK\n"
    unknown = "UNKNOWN\n"
    delivery = "DELIVERY"
    in_use = "IN-USE\n"
    busy = "BUSY\n"
    bad_request_header = "BAD-RQST-HDR\n"
    bad_request_body = "BAD-RQST-BODY\n"