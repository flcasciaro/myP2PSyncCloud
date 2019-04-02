""""This script contains function that will be invoked by the server's thread in order
to serve clients request"""

import utilities

def handshake(message, thread, peers):
    """add or update information (IP, Port) about a peer
    no peersLock, should be thread safe because only a thread is in charge of a peer"""

    peerID = message.split()[1]
    thread.peerID = peerID

    message = "HELLO {}".format(peerID)
    thread.client_sock.send(message.encode('ascii'))


def sendList(thread, groups, previous):
    """This function can retrieve the list of previous (already joined, previous=True) groups
    or the list of not-joined groups (previous = False) for a certain peerID"""
    groupList = list()

    for g in groups.values():
        if thread.peerID in g["peers"] and previous:
            groupList.append(utilities.hideGroupInfo(g))
            continue
        if thread.peerID not in g["peers"] and not previous:
            groupList.append(utilities.hideGroupInfo(g))

    thread.client_sock.send(str(groupList).encode('ascii'))

def restoreGroup(message, thread, groups):
    """"make the user active in one of its group"""

    groupName = message.split()[2]
    if groupName in groups:
            if thread.peerID in groups[groupName]["peers"]:
                if not groups[groupName]["peers"][thread.peerID]["active"]: #if not already active
                    groups[groupName]["peers"][thread.peerID]["active"] = True
                    answer = "GROUP {} RESTORED".format(groupName)
                    groups[groupName]["active"] += 1
                else:
                    answer = "IT'S NOT POSSIBLE TO RESTORE GROUP {} - PEER ALREADY ACTIVE".format(groupName)
            else:
                answer = "IT'S NOT POSSIBLE TO RESTORE GROUP {} - PEER DOESN'T BELONG TO IT".format(groupName)
    else:
        answer = "IT'S NOT POSSIBLE TO RESTORE GROUP {} - GROUP DOESN'T EXIST".format(groupName)

    thread.client_sock.send(answer.encode('ascii'))

def joinGroup(message, thread, groups):
    """"make the user active in a new group group
    choosing also the role as function of the token provided"""

    groupName = message.split()[2]
    tokenProvided = message.split()[4]

    if groupName in groups:
        if tokenProvided == groups[groupName]["tokenRW"] or tokenProvided == groups[groupName]["tokenRO"]:
            groups[groupName]["peers"][thread.peerID] = dict()
            groups[groupName]["peers"][thread.peerID]["peerID"] = thread.peerID
            groups[groupName]["peers"][thread.peerID]["active"] = True
            groups[groupName]["active"] += 1
            groups[groupName]["total"] += 1
            if tokenProvided == groups[groupName]["tokenRW"]:
                groups[groupName]["peers"][thread.peerID]["role"] = "RW"
                answer = "GROUP {} JOINED IN ReadWrite MODE".format(groupName)
            elif tokenProvided == groups[groupName]["tokenRO"]:
                groups[groupName]["peers"][thread.peerID]["role"] = "RO"
                answer = "GROUP {} JOINED IN ReadOnly MODE".format(groupName)
        else:
            answer = "IMPOSSIBLE TO JOIN GROUP {} - WRONG TOKEN".format(groupName)
    else:
        answer = "IMPOSSIBLE TO JOIN GROUP {} - GROUP DOESN'T EXIST".format(groupName)

    thread.client_sock.send(answer.encode('ascii'))

def createGroup(message, thread, groups):
    """This function allows a peer to create a new synchronization group
    specifying the groupName and the tokens. The creator peer become also the master
    of the new group."""

    newGroupName = message.split()[2]
    newGroupTokenRW = message.split()[4]
    newGroupTokenRO = message.split()[6]

    if newGroupName not in groups:
        """create the new group and insert in the group dictionary"""
        groupInfo = list()
        groupInfo.append(newGroupName)
        groupInfo.append(newGroupTokenRW)
        groupInfo.append(newGroupTokenRO)
        groupInfo.append("1")     #initial total users value
        groupInfo.append("1")     #initial active users value

        newGroup = utilities.createGroupDict(groupInfo)
        newGroup["peers"][thread.peerID] = dict()
        newGroup["peers"][thread.peerID]["peerID"] = thread.peerID
        newGroup["peers"][thread.peerID]["role"] = "Master"
        newGroup["peers"][thread.peerID]["active"] = True
        groups[newGroupName] = newGroup
        answer =  "GROUP {} SUCCESSFULLY CREATED".format(newGroupName)
    else:
        answer =  "IMPOSSIBLE TO CREATE GROUP {} - GROUP ALREADY EXIST".format(newGroupName)

    thread.client_sock.send(answer.encode('ascii'))

def imHere(message, thread, peers):

    """store IP address and Port Number on which the peer can be contacted by other peers"""

    if thread.peerID not in peers:
        """unknown peer"""
        peers[thread.peerID] = dict()

    """unknown peer"""
    peers[thread.peerID]["peerIP"] = message.split()[1]
    peers[thread.peerID]["peerPort"] = message.split()[2]

def peerDisconnection(thread, groups, peers):
    """Disconnect the peer from all the synchronization groups setting the active value to False"""

    for group in groups:
        if thread.peerID in group["peers"]:
            group["peers"][thread.peerID]["active"] = False

    del peers[thread.peerID]
