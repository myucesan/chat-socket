""" 
    commands.py

    Commands to configure the Unreliable Chat Server. Used to test the correctness of code 
"""

from enum import Enum

class Command(Enum):
    set_drop = "SET DROP"
    set_flip = "SET FLIP"
    set_burst = "SET BURST"
    set_burst_len = "SET BURST-LEN"
    set_delay = "SET DELAY"
    set_delay_len = "SET DELAY-LEN"
    get_value_setting = "GET"
    reset = "RESET"
    set_ok = "SET-OK"