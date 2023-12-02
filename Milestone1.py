# simple client structure
# import socket module
import socket
import hashlib
import re
import time

# server name is the first argument
# VAYU = "127.0.0.1"
VAYU = "vayu.iitd.ac.in"
PORT = 9801
TEAMNAME = "2021CS11010_2021CS50604@Injustice_League"

# ===================================  Client Class =============================================

class Client:
    def __init__(self,packetSize,isDebug):
        #initialize the class
        self.freeze = 0.01            # 10 ms timeout and wait period
        self.host = VAYU
        self.port = PORT
        self.teamname = TEAMNAME
        self.vayu = VAYU
        self.fileSize = 0
        self.packetSize = packetSize
        self.dataStream = []
        self.debug = isDebug
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.packetLossCount = 0
        self.totalPackets = 0
        self.startTime = 0
        return


    def open_connection(self):
        #opens the connection with the server
        self.sock.connect((self.host, self.port))
        #set a timeout of 10 ms on the receiving packet 
        self.sock.settimeout(self.freeze) 
        return
    

    def close_connection(self):
        #closes the connection with server
        self.sock.close()
        return
    

    def send_datagram(self, datagram, offset = -1):
        #send the datagram
        self.sock.send(datagram)

        #server may or may not reply.
        #if server does not reply, then return a "#" string otherwise return the reply
        try:
            reply = self.sock.recv(4096).decode()
        except socket.timeout:
            reply = '#'
        return reply
    
    
    def receive_file_1(self):
        #based on iterative protocol

        datagram = "SendSize\nReset\n\n"
        sizereply = '#'

        while sizereply == '#':
            sizereply = self.send_datagram(datagram.encode())
            time.sleep(self.freeze*2)

        sizereply = re.findall(r'\d+',sizereply)[0]
        self.fileSize = int(sizereply)

        if(self.debug):
            print("File size is: ",self.fileSize)

        self.totalPackets = (self.fileSize//self.packetSize)+1

        if(self.debug):
            print("Total packets are: ",self.totalPackets)

        # initialize dataStream and rem Packets.
        self.dataStream = ['#'] * self.totalPackets
        remaining_packet = self.totalPackets
        time.sleep(self.freeze*2)
        while remaining_packet > 0:
            for i in range(0,self.totalPackets):
                if self.dataStream[i] =='#':
                    offset = i*self.packetSize
                    datagram = "Offset: "+str(offset)+"\nNumBytes: "+str(self.packetSize)+"\n\n"
                    time.sleep(self.freeze/2)
                    reply = self.send_datagram(datagram.encode(), offset)

                    if reply != '#':
                        # get the offset and numBytes from reply
                        offset_recv = int(re.findall(r'\d+',reply)[0])
                        # numBytes = int(re.findall(r'\d+',reply)[1])
                        correctedIndex = i

                        # --------------- HANDLE OFFSET ERROR -----------------
                        if (offset_recv != offset):
                            correctedIndex = (offset_recv//self.packetSize) 
                            if self.debug:
                                print("#### OFFSET ERROR ####")
                            if self.dataStream[correctedIndex] != '#':
                                continue
                        
                        try:
                            reply_split = reply.split('\n',3)

                            #  ------------- HANDLE SQUISHIFICATION ---------------
                            if(reply_split[2] == 'Squished'):
                                reply = reply_split[3][1:]
                                if self.debug:
                                    print(" ******* SQUISHED ******* ")
                            else:
                                reply = reply_split[3]   

                            # -------------- HANDLE LENGTH ERRORS ------------------
                            if(correctedIndex != self.totalPackets-1):
                                if (len(reply) != self.packetSize):
                                    if self.debug:
                                        print(" ***** LENGTH ERROR ***** ")
                                    continue
                            else:
                                if (len(reply) != (self.packetSize - (self.packetSize*self.totalPackets - self.fileSize) + 1)):
                                    if self.debug:
                                        print(" ***** LENGTH ERROR in LAST PACKET ***** ")
                                    continue
                            
                            # STORE THE PACKET IN DATA STREAM
                            self.dataStream[correctedIndex] = reply
                            remaining_packet -= 1
                            time.sleep(self.freeze/2)

                        # In case of any strange error -- *** START AFRESH ***
                        except:
                            if self.debug:
                                print("########### --- ERROR IN REPLY --- #############")
                            time.sleep(2*self.freeze)
                            break
                            
            if(self.debug):
                print("Remaining packets are: ",remaining_packet)
        return
    

    def write_in_log(self):
        #write the dataStream in log file
        with open("log.txt","w") as f:
            for i in range(0,self.totalPackets):
                if(i == self.totalPackets-1):
                    f.write("\n\n\n\n")
                f.write(self.dataStream[i])
        return
    

    def submit_file(self):
        #make a string of dataStream
        data = ''
        for i in range(self.totalPackets):
            data += self.dataStream[i]

        data = data[:-1]

        #hash the data
        hash = hashlib.md5(data.encode()).hexdigest()
        if(self.debug):
            print("Hash of file is: ",hash)
        #submit file to server
        datagram = "Submit: "+self.teamname+"\nMD5: "+hash+"\n\n"
        reply = ''
        while True:
            self.sock.send(datagram.encode())
            try:
                reply = self.sock.recv(4096).decode()
            except socket.timeout:
                continue
            rep_split = reply.split('\n',1)
            if self.debug:
                print("inside submit loop")
            if rep_split[0][0:7] == 'Result:':
                break
            else:
                time.sleep(self.freeze)

        submitResult = reply.split('\n',3)[0][8:9]

        print(reply)
        return submitResult

# ========================================  MAIN FUNCTION  ========================================

if __name__ == "__main__":
    #initialize the client
    client = Client(1448,False)
    #open the connection
    client.startTime = time.time()
    client.open_connection()

    #get file
    client.receive_file_1()

    #submit the file
    submitResult = client.submit_file()

    #close the connection
    client.close_connection()
    EndTime = time.time()

    if client.debug:
        print("Time taken is: ",EndTime-client.startTime)