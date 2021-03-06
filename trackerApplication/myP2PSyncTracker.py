"""
Project: myP2PSync
@author: Francesco Lorenzo Casciaro - Politecnico di Torino - UPC

This code runs a tracker server instance.
Can be run using: (sudo) python3 pathTo/myP2PSyncTracker.py

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.
"""

import json
import os
import select
import socket
import sys
from threading import Thread, Lock

import reqHandlers
from group import Group

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shared.networking as networking

# Main data structure for groups management.
# It's a dictionary where the key is the GroupName and the value is
# a Group object containing information about the group e.g. tokens, peers
groups = dict()
groupsLock = Lock()

# Secondary data structures for peers information.
# It's a dictionary where the key is the peerID and the value is
# another dictionary containing information about the peer e.g. peerIP and peerPort
peers = dict()

scriptPath, scriptName = os.path.split((os.path.abspath(__file__)))
scriptPath += "/"

groupsInfoFile = scriptPath + 'sessionFiles/groupsInfo.json'
groupsPeersFile = scriptPath + 'sessionFiles/groupsPeers.json'
groupsFilesFile = scriptPath + 'sessionFiles/groupsFiles.json'

zeroTierIP = None
PORT_NUMBER = 45154


def initTracker():
    """Initialize tracker server data structures
    Data structures are filled with data read from local text files if they exist"""

    global groups, peers

    previous = True
    try:
        f = open(groupsInfoFile, 'r')
        try:
            groupsJson = json.load(f)
            for group in groupsJson:
                groupName = group["groupName"]
                tokenRW = group["tokenRW"]
                tokenRO = group["tokenRO"]
                groups[groupName] = Group(groupName, tokenRW, tokenRO)
            del groupsJson
        except ValueError:
            return None
        f.close()
    except FileNotFoundError:
        print("No previous session status found")
        previous = False

    if previous:
        try:
            f = open(groupsPeersFile, 'r')
            try:
                peersJson = json.load(f)
                for peer in peersJson:
                    peerID = peer["peerID"]
                    groupName = peer["groupName"]
                    role = peer["role"]
                    groups[groupName].addPeer(peerID, False, role)
                del peersJson
            except ValueError:
                return None
            f.close()
        except FileNotFoundError:
            pass

        try:
            f = open(groupsFilesFile, 'r')
            try:
                filesJson = json.load(f)
                for file in filesJson:
                    groupName = file["groupName"]
                    filename = file["filename"]
                    filesize = file["filesize"]
                    timestamp = file["timestamp"]
                    groups[groupName].addFile(filename, filesize, timestamp)
                del filesJson
            except ValueError:
                return None
            f.close()
        except FileNotFoundError:
            pass

        print("Previous session status restored")


def saveState():
    """Save the state of groups and peers in order to allow to restore the session in future"""
    groupsJson = list()
    with open(groupsInfoFile, 'w') as f:
        for group in groups.values():
            groupInfo = dict()
            groupInfo["groupName"] = group.name
            groupInfo["tokenRW"] = group.tokenRW
            groupInfo["tokenRO"] = group.tokenRO
            groupsJson.append(groupInfo)
        json.dump(groupsJson, f, indent=4)
        del groupsJson

    peersJson = list()
    with open(groupsPeersFile, 'w') as f:
        for group in groups.values():
            for peer in group.peersInGroup.values():
                peerInfo = dict()
                peerInfo["peerID"] = peer.peerID
                peerInfo["groupName"] = group.name
                peerInfo["role"] = peer.role
                peersJson.append(peerInfo)
        json.dump(peersJson, f, indent=4)
        del peersJson

    filesJson = list()
    with open(groupsFilesFile, 'w') as f:
        for group in groups.values():
            for file in group.filesInGroup.values():
                fileInfo = dict()
                fileInfo["groupName"] = group.name
                fileInfo["filename"] = file.filename
                fileInfo["filesize"] = file.filesize
                fileInfo["timestamp"] = file.timestamp
                filesJson.append(fileInfo)
        json.dump(filesJson, f, indent=4)
        del filesJson


class Server:
    """
    Multithread server class that will manage incoming connections.
    For each incoming connection it will create a thread.
    This thread will manage the request and terminate.
    The server runs until the property __stop is equals to False.
    The port on which the server will listen is choosen among available ports.
    """

    def __init__(self, port, maxClients=5):
        """
        Initialize server.
        :param port: port number on which the server will be reachable
        :param maxClients: maximum number of incoming connections.
        :return: void
        """

        # Initialize the server with a host and port to listen to.
        # Provide a list of functions that will be used when receiving specific data
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))

        self.host = networking.getMyIP()
        self.port = port

        self.sock.listen(maxClients)
        self.sockThreads = []
        self.counter = 0  # Will be used to give a number to each thread, can be improved (re-assigning free number)
        self.__stop = False

        # Accept an incoming connection.
        # Start a new SocketServerThread that will handle the communication.
        print('Starting socket server (host {}, port {})'.format(self.host, self.port))

        while not self.__stop:
            try:
                self.sock.settimeout(1)
                try:
                    clientSock, clientAddr = self.sock.accept()
                except socket.timeout:
                    clientSock = None

                if clientSock:
                    clientThr = SocketServerThread(clientSock, clientAddr, self.counter)
                    self.counter += 1
                    self.sockThreads.append(clientThr)
                    clientThr.daemon = True
                    clientThr.start()
            except KeyboardInterrupt:
                self.stopServer()

        self.closeServer()

    def closeServer(self):
        """ Close the client socket threads and server socket if they exists. """
        print('Closing server socket (host {}, port {})'.format(self.host, self.port))

        for thr in self.sockThreads:
            thr.stop()

        if self.sock:
            self.sock.close()

        print("Saving the state of the server")
        saveState()

        networking.leaveNetwork()

        exit()

    def stopServer(self):
        """This function will be called in order to stop the server (example using the X on the GUI or a signal)"""
        self.__stop = True


class SocketServerThread(Thread):
    def __init__(self, clientSock, clientAddr, number):
        """ Initialize the Thread with a client socket and address """
        Thread.__init__(self)
        self.clientSock = clientSock
        self.clientAddr = clientAddr
        self.number = number
        self.__stop = False

    def run(self):

        # print("[Thr {}] SocketServerThread starting with client {}".format(self.number, self.clientAddr))

        while not self.__stop:
            if self.clientSock:
                # Check if the client is still connected and if data is available:
                try:
                    rdyRead, __, __ = select.select([self.clientSock, ], [self.clientSock, ], [], 5)
                except select.error:
                    print('[Thr {}] Select() failed on socket with {}'.format(self.number, self.clientAddr))
                    self.stop()
                    return

                if len(rdyRead) > 0:
                    readData = networking.myRecv(self.clientSock)

                    # Check if socket has been closed
                    if len(readData) == 0:
                        print('[Thr {}] {} closed the socket.'.format(self.number, self.clientAddr))
                        self.stop()
                    else:
                        # Strip newlines just for output clarity
                        message = readData.rstrip()
                        messageFields = message.split(' ', 1)
                        # divide peerID from the request
                        peerID = messageFields[0]
                        request = messageFields[1]
                        self.manageRequest(request, peerID)
            else:
                print("[Thr {}] No client is connected, SocketServer can't receive data".format(self.number))
                self.stop()
        self.close()

    def stop(self):
        """ Stop the socket server thread."""
        self.__stop = True

    def close(self):
        """ Close connection with the client socket. """
        if self.clientSock:
            # print('[Thr {}] Closing connection with {}'.format(self.number, self.clientAddr))
            self.clientSock.close()

    def manageRequest(self, request, peerID):
        """
        Serves clients different requests.
        :param request: incoming requested stripped of the peerID
        :param peerID: id of the peer
        :return: void
        """

        # all the requests (stripped of the peerID) are identified using the first word
        # e.g. <action> <parameters>
        action = request.split()[0]

        # don't show common requests in the output of the tracker
        if action != "PEERS" and action != "BYE" and action != "GROUPS":
            print('[Thr {}] [Peer: {}] Received {}'.format(self.number, peerID, request))

        if action == "INFO":
            answer = str((zeroTierIP, PORT_NUMBER))
            networking.mySend(self.clientSock, answer)

        if action == "GROUPS":
            answer = reqHandlers.sendGroups(groups, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "RESTORE":
            answer = reqHandlers.restoreGroup(request, groups, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "JOIN":
            answer = reqHandlers.joinGroup(request, groups, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "CREATE":
            answer = reqHandlers.createGroup(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "ROLE":
            answer = reqHandlers.manageRole(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "PEERS":
            answer = reqHandlers.retrievePeers(request, groups, peers, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "ADDED_FILES":
            answer = reqHandlers.addedFiles(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "UPDATED_FILES":
            answer = reqHandlers.updatedFiles(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "REMOVED_FILES":
            answer = reqHandlers.removedFiles(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "GET_FILES":
            answer = reqHandlers.getFiles(request, groups, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "HERE":
            answer = reqHandlers.imHere(request, peers, peerID, self.clientAddr)
            networking.mySend(self.clientSock, answer)

        elif action == "LEAVE":
            answer = reqHandlers.leaveGroup(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "DISCONNECT":
            answer = reqHandlers.disconnectGroup(request, groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "EXIT":
            answer = reqHandlers.peerExit(groups, groupsLock, peerID)
            networking.mySend(self.clientSock, answer)

        elif action == "BYE":
            answer = "OK - BYE PEER"
            networking.mySend(self.clientSock, answer)
            self.stop()

        else:
            answer = "ERROR - UNEXPECTED REQUEST"
            networking.mySend(self.clientSock, answer)


if __name__ == '__main__':
    # tracker application main function

    # read previous session files and initialize tracker data structure
    initTracker()

    # joins ZeroTier network
    zeroTierIP = networking.joinNetwork()

    # run the tracker server until CTRL+C interrupt
    server = Server(PORT_NUMBER)
