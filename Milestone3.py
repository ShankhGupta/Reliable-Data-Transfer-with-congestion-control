# simple client structure
# import socket module
import socket
import hashlib
import re
import time
import matplotlib.pyplot as plt
# import numpy as np

# server name is the first argument
# VAYU = "127.0.0.1"
# VAYU = "10.17.6.5"
# VAYU = "vayu.iitd.ac.in"    
VAYU = "10.17.7.218"           
# VAYU = "10.17.7.134"
"""
New Ideas to try:
    1) make a different wait time for sending requests and learn it when received packed it not the one we want
    2) try to increase congestion window by seeing the wait time and traffic on the network
    3) """
# VAYU = "10.17.51.115"    
PORT = 9802
TEAMNAME = "2021CS11010_2021CS50604@Injustice_League"

Xpoints_req = []
Ypoints_req = []

Xpoints_reply = []
Ypoints_reply = []

IS_Squished = False

# ===================================  Client Class =============================================

class Client:
    def __init__(self,packetSize,isDebug):
        #initialize the class
        self.cnwd = 4  # size of burst to be sent  updated in the get_size() funtion
        self.requestArray = []  # stores the offset which needs to be requested from the server
        self.datastream = []   # stores the data received from the server
        self.pltGraph = False
        self.fileSize = 0
        self.totalPackets = 0
        self.host  =  VAYU
        self.port = PORT
        self.teamname = TEAMNAME
        self.packetSize = packetSize
        self.debug = isDebug
        self.bufferSize = 32768
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)


        # tunable parameters:
        self.freeze = 0.004
        self.lossThreshold = 0
        self.waitTime = 0.025
        return
    
    def open_connection(self):
        #opens the connection with the server
        self.sock.connect((self.host, self.port))
        #set a timeout of 10 ms on the receiving packet 
        self.sock.settimeout(0.004)
        return
    

    def close_connection(self):
        #closes the connection with server
        self.sock.close()
        return
    

    def send_datagram(self, datagram, offset = -1):
        #send the datagram
        RTTstart  = time.time()
        self.sock.send(datagram)
        # if(offset > 0):
            # Xpoints_req.append(time.time()-self.startTime)
            # Ypoints_req.append(offset)

        #server may or may not reply.
        #if server does not reply, then return a "#" string otherwise return the reply
        try:
            reply = self.sock.recv(self.bufferSize).decode()
            # Xpoints_reply.append(time.time()-self.startTime)
            # Ypoints_reply.append(offset)
            RTTend = time.time()
            RTT = RTTend - RTTstart
            if self.debug:
                print("RTT is: ",RTT)
            # self.freeze = max(RTT, self.freeze)
        except socket.timeout:
            reply = '#'
        return reply
    

    def get_size(self):
        #get the size of file from server
        datagram = "SendSize\nReset\n\n"
        reply = '#'
        while reply == '#':
            reply = self.send_datagram(datagram.encode())
            time.sleep(self.freeze) # i dont think this is needed

        self.fileSize = int(re.findall(r'\d+',reply)[0])
        self.totalPackets = (self.fileSize//self.packetSize) + 1

        # init the request array to all the packets, as all are to be requested initially
        for i in range(self.totalPackets):
            self.requestArray.append(i)

        self.cnwd = min(self.cnwd, self.totalPackets - 1)
        if(self.debug):
            print("File size is: ",self.fileSize)
            print("Total packets are: ",self.totalPackets)
        return
    

    def checkPacket(self, reply):
        global IS_Squished
        recvOffset = int(re.findall(r'\d+',reply)[0])
        pkt_index = recvOffset//self.packetSize
        try:
            reply_split = reply.split('\n',3)
        
            #  ------------- HANDLE SQUISHIFICATION ---------------
            if(reply_split[2] == 'Squished'):
                reply = reply_split[3][1:]
                IS_Squished = True
                # time.sleep(self.freeze*50)
                if self.debug:
                    print(" ******* SQUISHED ******* ")
                time.sleep(5*self.freeze)
            else:
                reply = reply_split[3]   
                IS_Squished = False

            # -------------- HANDLE LENGTH ERRORS ------------------
            if(pkt_index != self.totalPackets-1):
                if (len(reply) != self.packetSize):
                    if self.debug:
                        print(" ***** LENGTH ERROR ***** ")
                    return '#', -1
            else:
                if (len(reply) != (self.packetSize - (self.packetSize*self.totalPackets - self.fileSize) + 1)):
                    if self.debug:
                        print(" ***** LENGTH ERROR in LAST PACKET ***** ")
                    return '#', -1
            
            # STORE THE PACKET IN DATA STREAM
            return reply, pkt_index
        
        # In case of any strange error :
        except:
            if self.debug:
                print("########### --- ERROR IN REPLY --- #############")
            time.sleep(2*self.freeze)
            return '#', -1     


    def receive_file(self):
        """""
        Protocol idea :
            1) request the packets in the range [0, cnwd]
            2) wait for sone time for the packets to arrive
            3) iterate over the packets received and put them in the datastream
            4) for those packets which are not received, make a new request array and append it there
            5) after the first iteration over all the packets, replace the old request array with the new one
            6) repeat the process until all the packets are received
            7) learn the RTT and congestion window size
        """""
        
        self.get_size()
        self.datastream = ['#'] * self.totalPackets # initialize dataStream
        # remaining_packet = self.totalPackets

        while len(self.requestArray) > 0:
            startIndex = 0
            if self.debug:
                print("Remaining packets are:", len(self.requestArray))
                print("=====================================================")
            while startIndex < len(self.requestArray):
                st = time.time()
                for j in range(self.cnwd):
                    if (startIndex + j < len(self.requestArray)):
                        if(self.datastream[self.requestArray[startIndex + j]] == '#'):
                            offset = (self.requestArray[startIndex + j]) * self.packetSize
                            datagram = "Offset: " + str(offset) +"\nNumBytes: "+str(self.packetSize)+"\n\n"
                            self.sock.send(datagram.encode())

                time.sleep(self.freeze/4)
                st += self.freeze/4

                lossCount = 0
                for j in range(self.cnwd):
                    try:
                        reply = self.sock.recv(self.bufferSize).decode()
                        reply, pkt_index = self.checkPacket(reply)
                        if(reply != '#'):
                            if (self.datastream[pkt_index] == '#'):
                                self.datastream[pkt_index] = reply
                                self.requestArray.remove(pkt_index)
                    except socket.timeout:
                        lossCount += 1
                        continue
                
                time.sleep(self.freeze*2)
                st += self.freeze*2

                startIndex += self.cnwd

                if(lossCount > self.lossThreshold):
                    self.cnwd = max(self.cnwd//2, 2)
                else:
                    self.cnwd += 1
                
                et = time.time()
                self.freeze = 0.825*self.freeze + 0.175*(et-st)


                time.sleep(self.freeze*0.8)

                if(self.debug):
                    print("Freeze time is: ", self.freeze + self.waitTime)
                    print("CNWD Size:", self.cnwd)
                    print("Request array is: ",len(self.requestArray))
            
        return
    

    def write_in_log(self):
        #write the datastream in log file
        with open("log.txt","w") as f:
            for i in range(0,self.totalPackets):
                if(i == self.totalPackets-1):
                    f.write("\n\n\n\n")
                f.write(self.datastream[i])
        return
    

    def submit_file(self):
        #make a string of datastream
        data = ''
        for i in range(self.totalPackets):
            data += self.datastream[i]

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
                reply = self.sock.recv(self.bufferSize).decode()
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
    client = Client(1448,True)
    
    #open the connection
    startTime = time.time()
    client.open_connection()

    #get file
    client.receive_file()

    #submit the file
    submitResult = client.submit_file()

    #close the connection
    client.close_connection()
    endTime = time.time()

    if client.debug:
        print("Time taken is: ",endTime-startTime)
    