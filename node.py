from __future__ import print_function
import socket
import datetime
import random
import threading
from time import sleep
import unicast as u
import BasicMulticast as basic
import FIFOMulticast as f
import TotalMulticast as t


class node():

    def __init__(self, ID = -1, IP = "", PORT = 0, SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) ):
        self.RECEIVED = []
        self.DESTINATIONS = []
        self.MYID = ID
        self.MYIP = IP
        self.MYPORT = PORT
        self.MYSOCKET = SOCKET
        self.MIN = 0
        self.MAX = 0
        self.MULTITYPE = 0
        self.FIFO = None
        self.TOTAL = None
        self.BASIC = None
        self.SEQUENCERCOUNTER = 0

    def __str__(self):
        return (str(self.MYID) + "|"+ self.MYIP +"|"+ str(self.MYPORT) )
    __repr__ = __str__
    def make_node(self):

        # Opens the configuration file
        # The config file lists each node's characteristics, each on a separate line
        # The three characteristics right now are ID Number, IP Address, and Port Number

        config_file = open("config","r")

        # Number of nodes in config file
        # -2 to account for first min-max line, and two trailing whitespace line

        NUMOFNODES = sum(1 for line in open('config')) - 2

        # Instantiate multi Objects

        self.FIFO = f.FIFOMulticast(self,NUMOFNODES)
        self.TOTAL = t.TotalMulticast(self)
        self.BASIC = basic.BasicMulticast()

        # Take min and max delay from config file

        minmaxdelay = config_file.readline().rstrip('\n')
        minandmax = minmaxdelay.split(" ")
        self.MIN = int(minandmax[0])
        self.MAX = int(minandmax[1])

        for a in range(NUMOFNODES):


            # Read in the ID, IP, and PORT from the config file for each of the four connections

            line = config_file.readline().rstrip('\n')

            # Split line into ID, IP, PORT

            linearray = line.split(" ")
            ID = int(linearray[0])
            IP = str(linearray[1])
            PORT = int(linearray[2])

            # Decides which node this process will be

            if self.MYID == -1:
                self.MULTITYPE = int(raw_input("Type in your Multicast ordering type: 1 for FIFO, 2 for TO, 3 for CO"))
                self.MYID = int(raw_input("Type in your node ID number (0-3) 0 is sequencer for TO"))

            # Creates sockets between all pairs of nodes and
            # appends nodes to a list as a tuple of ID, IP, PORT
            # and SOCK
            SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            if a == self.MYID:
                self.MYIP = IP
                self.MYPORT = PORT
                self.MYSOCKET = SOCK
                self.MYSOCKET.bind((self.MYIP, self.MYPORT)) # Port of processNumber

            self.DESTINATIONS.append(node(ID,IP,PORT,SOCK))

        # Bind socket to the process


    # Method run on separate thread to listen for other nodes sending it messages
    # Reacts differently to different message types (unicast, FIFO, etc.)

    def receive(self):


        while 1:

            # Socket receiving data. Closes the thread if "close" is received.

            data = self.MYSOCKET.recv(1024)
            if data == "close": break
            threading.Thread(target= self.delay,args=((data,))).start()

 
                    
    def delay(self,data):

            # Delays
            delaytime = random.uniform(self.MIN,self.MAX)/1000
            sleep(delaytime)

           #Split message into different parts
            datasplit = data.split(" ") 
            id = int(datasplit[0])
            data = datasplit[1]

            # UNICAST

            if(len(datasplit) == 2):
                self.RECEIVED.append((id,data))
                u.unicast_receive(self,self.DESTINATIONS[id],data)
            
            # FIFO
            # Compares messager on sequencer to vector sequencer. Refer to FIFO algorithm

            elif(self.MULTITYPE == 1): 
                Rsequencer = int(self.FIFO.RSEQUENCERS[id])
                Ssequencer = int(datasplit[2])
                if(Ssequencer == Rsequencer + 1):
                    print("Message accepted")
                    self.FIFO.deliver(self.DESTINATIONS[id],data)
                    for queued in self.FIFO.QUEUE:
                        qid = queued[0]
                        qdata = queued[1]
                        qRsequencer = queued[2]
                        if(Ssequencer== qRsequencer + 1):
                            self.FIFO.deliver(self.DESTINATIONS[qid],qdata)
                            self.FIFO.QUEUE.remove(queued)
                elif(Ssequencer < Rsequencer + 1):
                    print("Message rejected")
                else:
                    print("Message appended")
                    self.FIFO.QUEUE.append((id,data,Rsequencer))

            # Total Order

            elif(self.MULTITYPE == 2):
                counter = int(datasplit[2])
                if(self.MYID == 0): # For sequencer
                    message = str(id) + " " + data + " " + str(counter) + " order " + str(self.SEQUENCERCOUNTER)
                    self.BASIC.multicast(self.DESTINATIONS[1:], message)
                    self.SEQUENCERCOUNTER = self.SEQUENCERCOUNTER + 1
                else:
                    if(len(datasplit) > 3):
                        if(datasplit[3] == "order"):
                            for a in self.TOTAL.QUEUE:
                                for b in self.TOTAL.QUEUE:
                                    if(self.SEQUENCERCOUNTER == self.TOTAL.COUNTER and b[1]==id and b[2]==counter):
                                        self.TOTAL.deliver(self.DESTINATIONS[id],data)
                                        self.TOTAL.COUNTER = self.SEQUENCERCOUNTER + 1
                    else:
                        self.TOTAL.QUEUE.append((data, id, counter, self.SEQUENCERCOUNTER))


    def action_loop(self):

        # Receive thread

        threading.Thread(target= self.receive).start()

        # Send messages to other nodes using the format:
        # For unicast:      send (# of node) (message)
        # For multicast:    msend (message)
        # type in 'close' to exit to terminal   
        
        while 1:
            decide = raw_input("What do you want to do?\n")
            if(decide[0:4] == "send"):
                sendTo = int(decide[5])
                sendString = decide[7:]
                sendString = str(self.MYID) + " " + sendString
                u.unicast_send(self.DESTINATIONS[sendTo], sendString)
            if(decide[0:5] == "close"):
                u.unicast_send(self.DESTINATIONS[self.MYID], "close")
                break
            if(decide[0:5] == "msend"):
                sendString = decide[6:]
                sendString = str(self.MYID) + " " + sendString
                if(self.MULTITYPE == 1):
                    self.FIFO.multicast(self.DESTINATIONS,sendString)
                if(self.MULTITYPE == 2):
                    self.TOTAL.multicast(self.DESTINATIONS,sendString)

# Run the node

run = node()
run.make_node()
run.action_loop()