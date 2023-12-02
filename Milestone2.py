# simple client structure
# import socket module
import socket
import hashlib
import re
import time

# server name is the first argument
# VAYU = "127.0.0.1"
# VAYU = "10.17.6.5"
# VAYU = "vayu.iitd.ac.in"        # not working
# VAYU = "10.17.7.218"            # not working
# VAYU = "10.17.7.134"
VAYU = "10.17.51.115"     # not working
PORT = 9801
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

        # parameters to tune :
        self.freeze = 0.005 # localhost : 4ms   vayu : 4ms
        self.cnwd = 6
        self.freezeInit = 0.008
        self.freezeReg = 0.005
        self.thresholdCount = 20
        self.maxCoolDown = 3
        self.pltGraph = False

        # static parameters
        self.host = VAYU
        self.port = PORT
        self.teamname = TEAMNAME
        self.fileSize = 0
        self.packetSize = packetSize
        self.dataStream = []
        self.debug = isDebug
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.packetLossCount = 0
        self.totalPackets = 0
        self.startTime = 0.0
        self.bufferSize = 32768
        self.itCount = 0
        self.thresholdCrossed = False
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
        RTTstart  = time.time()
        self.sock.send(datagram)
        # if(offset > 0):
            # Xpoints_req.append(time.time()-self.startTime)
            # Ypoints_req.append(offset)

        #server may or may not reply.
        #if server does not reply, then return a "#" string otherwise return the reply
        try:
            reply = self.sock.recv(4096).decode()
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
            # time.sleep(self.freeze)# i dont think this is needed

        self.fileSize = int(re.findall(r'\d+',reply)[0])
        self.totalPackets = (self.fileSize//self.packetSize) + 1
        self.maxCoolDown = self.cnwd - 1

        self.cnwd = min(10, self.totalPackets - 1)
        if(self.debug):
            print("File size is: ",self.fileSize)
            print("Total packets are: ",self.totalPackets)
        return
    

    def checkPacket(self, reply, pkt_index):
        try:
            reply_split = reply.split('\n',3)
        
            #  ------------- HANDLE SQUISHIFICATION ---------------
            if(reply_split[2] == 'Squished'):
                reply = reply_split[3][1:]
                IS_Squished = True
                time.sleep(self.freeze*20)
                if self.debug:
                    print(" ******* SQUISHED ******* ")
            else:
                reply = reply_split[3]   

            # -------------- HANDLE LENGTH ERRORS ------------------
            if(pkt_index != self.totalPackets-1):
                if (len(reply) != self.packetSize):
                    if self.debug:
                        print(" ***** LENGTH ERROR ***** ")
                    return '#'
            else:
                if (len(reply) != (self.packetSize - (self.packetSize*self.totalPackets - self.fileSize) + 1)):
                    if self.debug:
                        print(" ***** LENGTH ERROR in LAST PACKET ***** ")
                    return '#'
            
            # STORE THE PACKET IN DATA STREAM
            return reply
        
        # In case of any strange error :
        except:
            if self.debug:
                print("########### --- ERROR IN REPLY --- #############")
            time.sleep(2*self.freeze)
            return '#'     


    def receive_file(self):
        #receive the file from the server
        self.get_size()
        self.dataStream = ['#'] * self.totalPackets # initialize dataStream
        remaining_packet = self.totalPackets
        self.thresholdCount = self.totalPackets//1000

        cwdStart = 0
        cwdEnd = min(self.cnwd, self.totalPackets)
        cooldown = self.maxCoolDown
        
        self.freeze = self.freezeInit
        #initialize the window
        for i in range(cwdStart,cwdEnd):
            if self.dataStream[i] =='#':
                offset = i*self.packetSize
                datagram = "Offset: "+str(offset)+"\nNumBytes: "+str(self.packetSize)+"\n\n"
                self.sock.send(datagram.encode())

                if self.pltGraph:
                    Xpoints_req.append(time.time() - self.startTime)
                    Ypoints_req.append(offset)

                time.sleep(self.freeze)

        while remaining_packet > 0:
            st = time.time()
            try:
                reply = self.sock.recv(self.bufferSize).decode()

                if self.pltGraph:
                    recvOffset = int(re.findall(r'\d+',reply)[0])
                    Xpoints_reply.append(time.time() - self.startTime)
                    Ypoints_reply.append(recvOffset)

            except:
                datagram = "Offset: "+str(cwdStart*self.packetSize)+"\nNumBytes: "+str(self.packetSize)+"\n\n"
                self.sock.send(datagram.encode())
                time.sleep(self.freeze*2)
                st += self.freeze*2 - 0.008
                continue
            
            recvOffset = int(re.findall(r'\d+',reply)[0])

            if (self.dataStream[(recvOffset//self.packetSize)] != '#'):
                continue

            if cwdStart*self.packetSize == recvOffset:
                reply = self.checkPacket(reply, cwdStart)
                if reply != '#':
                    self.dataStream[cwdStart] = reply
                    remaining_packet -= 1
                else:
                    continue

                while self.dataStream[cwdStart] != '#' and cwdStart < cwdEnd:
                    cwdStart += 1
                
                while (cwdEnd - cwdStart < self.cnwd):
                    if (cwdEnd == self.totalPackets - 1):
                        break
                    cwdEnd += 1
                    datagram = "Offset: "+str(cwdEnd*self.packetSize)+"\nNumBytes: "+str(self.packetSize)+"\n\n"
                    self.sock.send(datagram.encode())

                    if self.pltGraph:
                        Xpoints_req.append(time.time() - self.startTime)
                        Ypoints_req.append(cwdEnd*self.packetSize)

                    time.sleep(self.freeze)
                    st += self.freeze - 0.004

            else:
                cooldown -= 1

                if(cooldown == 0):
                    datagram = "Offset: "+str(cwdStart*self.packetSize)+"\nNumBytes: "+str(self.packetSize)+"\n\n"
                    self.sock.send(datagram.encode())
                    time.sleep(self.freeze/2)
                    st += self.freeze/2 - 0.002
                    if self.pltGraph:
                        Xpoints_req.append(time.time() - self.startTime)
                        Ypoints_req.append(cwdStart*self.packetSize)

                    cooldown = self.maxCoolDown

                pktIndex = (recvOffset//self.packetSize)
                reply = self.checkPacket(reply, pktIndex)
                if reply == '#':
                    continue
                self.dataStream[pktIndex] = reply
                remaining_packet -= 1
                if (cwdEnd < self.totalPackets - 1):
                    cwdEnd += 1
                    datagram = "Offset: "+str(cwdEnd*self.packetSize)+"\nNumBytes: "+str(self.packetSize)+"\n\n" 
                    self.sock.send(datagram.encode())
                    time.sleep(self.freeze)
                    st += self.freeze - 0.004

                if self.pltGraph:
                    Xpoints_req.append(time.time() - self.startTime)
                    Ypoints_req.append(cwdEnd*self.packetSize)
            et = time.time()
            # make self.freeze to be running average of et-st
            
            if self.itCount > self.thresholdCount:
                if not self.thresholdCrossed:
                    self.freeze = self.freezeReg
                    self.thresholdCrossed = True
                    
                self.freeze = 0.875*self.freeze + 0.125*((et-st))
            else:
                self.freeze = self.freezeInit

            if self.debug:
                print("Freeze is: ",self.freeze)
            self.itCount += 1
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
    client = Client(1448,False)
    
    #open the connection
    client.startTime = time.time()
    client.open_connection()

    #get file
    client.receive_file()

    #submit the file
    submitResult = client.submit_file()

    #close the connection
    client.close_connection()
    EndTime = time.time()

    if client.debug:
        print("Time taken is: ",EndTime-client.startTime)
    
