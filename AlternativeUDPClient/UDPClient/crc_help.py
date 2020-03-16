POLYNOMIAL = "100000100110000010001110110110111"

def convert_crc(message):

    code = ""
    message_in_bytes = message.encode()
    for byte in message_in_bytes:
        code += bin(byte)[2:]

    empty_remainder = ""
    for i in range(len(POLYNOMIAL)-1):
        empty_remainder += "0"

    to_calculate = code + empty_remainder
    counter = 0
    while counter <= len(to_calculate)-len(POLYNOMIAL):
        if int(to_calculate[counter]) == 1:
            for id, bit in enumerate(POLYNOMIAL):                 
                result = int(to_calculate[counter+id]) ^ int(bit)
                to_calculate = to_calculate[:counter+id] + str(result) + to_calculate[counter+id+1:]
                
        counter += 1
    remainder = to_calculate[((len(POLYNOMIAL)-1)*-1):]
    return int(remainder, 2).to_bytes(4, byteorder="big")
    

def detect_crc(data):
    # We already know that the last 4 bytes contain the remainder
    remainder_string = bin(int.from_bytes(data[-4:], byteorder="big"))[2:]
    # As remainder has to be 32 bits, we append 0s in beginning, if len of remainder is less than 32
    while len(remainder_string) != len(POLYNOMIAL)-1:
        remainder_string ="0" + remainder_string
    
    # Extract the message from the remainder
    message_data = data[:-4]
    
    message_string = ""

    for byte in message_data:
        message_string += bin(byte)[2:]

    # Append them together again for calculation
    to_calculate = message_string + remainder_string

    counter = 0
    while counter <= len(to_calculate)-len(POLYNOMIAL): 
        if int(to_calculate[counter]) == 1:
            for id, bit in enumerate(POLYNOMIAL):
                result = int(to_calculate[counter+id]) ^ int(bit)
                to_calculate = to_calculate[:counter+id] + str(result) + to_calculate[counter+id+1:]
                
        counter += 1

    if to_calculate.count("1") > 0:
        return [False, None]
    else:
        return [True, message_data.decode()]