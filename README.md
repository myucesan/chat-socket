# Chat client using sockets

A server has been supplied by a university, this server will not be available all the time. A self-made server will be added to this repository at a later date. You can then run the server at your convenience.

## Instructions

To run the program:

`python3 client.py`

When you start the program it connects to the supplied server (which, at this time, will be only available at the current period). It asks to enter a name, you can enter any name you like as long as it is only alphanumerical and does not contain spaces. The following commands are available.

- !who - shows a list of names that are connected to the server
- @[username] [message] - sends message to given username (for eg. @James hey man), is capital sensitive
- !quit - used to disconnect from the server and end the program

This client has been tested using Python3.

# Unreliable UDP Network solutions

- Flip bits:
- Drop messages: Set socket on non-blocking. Add at sending client some variable that expects ACK, and keep checking after every little bit if ACK received. If not, retransmit. For receiving client, message may come, so add a list containing duplicate msgs so they wont be shown to client again. Remove it after a very small timer. 
- Delays:
- Bursts: