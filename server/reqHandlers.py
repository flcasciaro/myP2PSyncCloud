""""This code contains functions that will be invoked by the server's threads in order
to serve clients request.
@author: Francesco Lorenzo Casciaro - Politecnico di Torino - UPC"""

from group import Group


def imHere(request, peers, peerID, publicAddr):

    """store IP address and Port Number on which the peer can be contacted by other peers"""

    if peerID not in peers:
        """unknown peer"""
        peers[peerID] = dict()

    peers[peerID]["privateAddr"] = (request.split()[1], request.split()[2])
    peers[peerID]["publicAddr"] = (publicAddr[0], request.split()[2])

    print(peers[peerID])

    answer = "OK - {}".format(publicAddr[0])
    return answer



def sendGroups(groups, peerID):
    """This function can retrieve the list of active, previous or other groups for a certain peerID"""
    groupsList = dict()

    for g in groups.values():
        if peerID in g.peersInGroup:
            if g.peersInGroup[peerID].active:
                role = g.peersInGroup[peerID].role
                groupsList[g.name] = g.getPublicInfo(role,"ACTIVE")
            else:
                role = g.peersInGroup[peerID].role
                groupsList[g.name] = g.getPublicInfo(role,"RESTORABLE")
        else:
            groupsList[g.name] = g.getPublicInfo("","OTHER")


    return "OK - " + str(groupsList)


def restoreGroup(request, groups, peerID):
    """"make the user active in one of its group (already joined)"""

    groupName = request.split()[2]
    if groupName in groups:
            if peerID in groups[groupName].peersInGroup:
                if not groups[groupName].peersInGroup[peerID].active: #if not already active
                    groups[groupName].restorePeer(peerID)
                    answer = "OK - GROUP {} RESTORED".format(groupName)
                else:
                    answer = "ERROR - IT'S NOT POSSIBLE TO RESTORE GROUP {} - PEER ALREADY ACTIVE".format(groupName)
            else:
                answer = "ERROR - IT'S NOT POSSIBLE TO RESTORE GROUP {} - PEER DOESN'T BELONG TO IT".format(groupName)
    else:
        answer = "ERROR - IT'S NOT POSSIBLE TO RESTORE GROUP {} - GROUP DOESN'T EXIST".format(groupName)

    return answer

def joinGroup(request, groups, peerID):
    """"make the user active in a new group group
    choosing also the role as function of the token provided"""

    groupName = request.split()[2]
    tokenProvided = request.split()[4]

    if groupName in groups:
        if tokenProvided == groups[groupName].tokenRW or tokenProvided == groups[groupName].tokenRO:
            if tokenProvided == groups[groupName].tokenRW:
                role = "RW"
                answer = "OK - GROUP {} JOINED IN ReadWrite MODE".format(groupName)
            elif tokenProvided == groups[groupName].tokenRO:
                role = "RO"
                answer = "OK - GROUP {} JOINED IN ReadOnly MODE".format(groupName)
            groups[groupName].addPeer(peerID, True, role)

        else:
            answer = "ERROR - IMPOSSIBLE TO JOIN GROUP {} - WRONG TOKEN".format(groupName)
    else:
        answer = "ERROR - IMPOSSIBLE TO JOIN GROUP {} - GROUP DOESN'T EXIST".format(groupName)

    return answer

def createGroup(request, groups, peerID):
    """This function allows a peer to create a new synchronization group
    specifying the groupName and the tokens. The creator peer become also the master
    of the new group."""

    newGroupName = request.split()[2]
    newGroupTokenRW = request.split()[4]
    newGroupTokenRO = request.split()[6]

    if newGroupName not in groups:
        """create the new group and insert in the group dictionary"""

        newGroup = Group(newGroupName, newGroupTokenRW, newGroupTokenRO)
        newGroup.addPeer(peerID, True, "Master")
        groups[newGroupName] = newGroup

        answer =  "OK - GROUP {} SUCCESSFULLY CREATED".format(newGroupName)
    else:
        answer =  "ERROR - IMPOSSIBLE TO CREATE GROUP {} - GROUP ALREADY EXIST".format(newGroupName)

    return answer

def manageRole(request, groups, groupsLock, peerID):

    action = request.split()[1]
    modPeerID = request.split()[2]
    groupName = request.split()[4]

    if action == "CHANGE_MASTER":
        newRole = "Master"
    elif action == "ADD_MASTER":
        newRole = "Master"
    elif action == "MAKE_IT_RW":
        newRole = "RW"
    elif action == "MAKE_IT_RO":
        newRole = "RO"

    if groupName in groups:
        """check if both peerIDs actually belongs to the group"""
        if peerID in groups[groupName].peersInGroup and modPeerID in groups[groupName].peersInGroup:
            if groups[groupName].peersInGroup[peerID].role.upper() == "MASTER":

                groupsLock.acquire()
                groups[groupName].peersInGroup[modPeerID].role = newRole

                if action.upper() == "CHANGE_MASTER":
                    groups[groupName].peersInGroup[peerID].role = "RW"

                groupsLock.release()
                answer = "OK - OPERATION ALLOWED"

            else:
                answer = "ERROR - OPERATION NOT ALLOWED"
        else:
            answer = "ERROR - OPERATION NOT ALLOWED"
    else:
        answer = "ERROR - GROUP {} DOESN'T EXIST".format(groupName)

    return answer

def retrievePeers(request, groups, peers, peerID):
    """"retrieve a list of peers (only active or all) for a specific group
    request format: "PEERS <GROUPNAME> <ACTIVE/ALL>"   """

    groupName = request.split()[1]
    selectAll = True if request.split()[2].upper() == "ALL" else False

    if groupName in groups:
        peersList = list()
        for peer in groups[groupName].peersInGroup:
            """skip inactive peers if selectAll is False"""
            if not groups[groupName].peersInGroup[peer].active and not selectAll:
                continue
            """skip the peer which made the request"""
            if peer == peerID:
                continue
            peerInfo = dict()
            peerInfo["peerID"] = peer
            peerInfo["privateAddr"] = peers[peer]["privateAddr"]
            peerInfo["publicAddr"] = peers[peer]["publicAddr"]
            peerInfo["active"] = groups[groupName].peersInGroup[peer].active
            peerInfo["role"] = groups[groupName].peersInGroup[peer].role
            peersList.append(peerInfo)
        answer = "OK - " + str(peersList)
    else:
        answer = "ERROR - GROUP {} DOESN'T EXIST".format(groupName)

    return answer

def addedFiles(request, groups, groupsLock, peerID):
    try:
        requestFields = request.split(" ", 2)
        groupName = requestFields[1]
        filesInfo = eval(requestFields[2])

        groupsLock.acquire()

        if groupName in groups:
            if peerID in groups[groupName].peersInGroup:
                if groups[groupName].peersInGroup[peerID].role.upper() == "RO":
                    answer = "ERROR - PEER DOESN'T HAVE ENOUGH PRIVILEGE"
                else:
                    for fileInfo in filesInfo:
                        groups[groupName].addFile(fileInfo["treePath"], fileInfo["filesize"], fileInfo["timestamp"])
                    answer = "OK - FILES SUCCESSFULLY ADDED"
            else:
                answer = "ERROR - PEER DOESN'T BELONG TO THE GROUP"
        else:
            answer = "ERROR - GROUP DOESN'T EXIST"
        groupsLock.release()

    except IndexError:
        answer = "ERROR - INVALID REQUEST"

    return answer


def removedFiles(request, groups, groupsLock, peerID):
    """request is REMOVE_FILES <groupname> <filesInfo>"""

    try:
        requestFields = request.split(" ", 2)
        groupName = requestFields[1]
        treePaths = eval(requestFields[2])

        groupsLock.acquire()

        if groupName in groups:
            if peerID in groups[groupName].peersInGroup:
                if groups[groupName].peersInGroup[peerID].role.upper() == "RO":
                    answer = "ERROR - PEER DOESN'T HAVE ENOUGH PRIVILEGE"
                else:
                    for tp in treePaths:
                        groups[groupName].removeFile(tp)
                    answer = "OK - FILES REMOVED FROM THE GROUP"
            else:
                answer = "ERROR - PEER DOESN'T BELONG TO THE GROUP"
        else:
            answer = "ERROR - GROUP DOESN'T EXIST"
        groupsLock.release()

    except IndexError:
        answer = "ERROR - INVALID REQUEST"

    return answer


def updatedFiles(request, groups, groupsLock, peerID):
    """request is UPDATE_FILES <groupname> <filesInfo>"""

    try:
        requestFields = request.split(" ", 2)
        groupName = requestFields[1]
        filesInfo = eval(requestFields[2])

        groupsLock.acquire()

        if groupName in groups:
            if peerID in groups[groupName].peersInGroup:
                if groups[groupName].peersInGroup[peerID].role.upper() == "RO":
                    answer = "ERROR - PEER DOESN'T HAVE ENOUGH PRIVILEGES"
                else:
                    for fileInfo in filesInfo:
                        groups[groupName].updateFile(fileInfo["treePath"], fileInfo["filesize"], fileInfo["timestamp"])
                    answer = "OK - FILES SUCCESSFULLY UPDATED"
            else:
                answer = "ERROR - PEER DOESN'T BELONG TO THE GROUP"
        else:
            answer = "ERROR - GROUP DOESN'T EXIST"
        groupsLock.release()

    except IndexError:
        answer = "ERROR - INVALID REQUEST"

    return answer

def getFiles(request, groups, peerID):

    try:
        groupName = request.split()[1]

        if groupName in groups:
            g = groups[groupName]
            if peerID in g.peersInGroup:

                filesInfo = list()
                for file in g.filesInGroup.values():
                    fileDict = dict()
                    fileDict["treePath"] = file.filename
                    fileDict["filesize"] = file.filesize
                    fileDict["timestamp"] = file.timestamp
                    filesInfo.append(fileDict)

                answer = "OK - " + str(filesInfo)

            else:
                answer = "ERROR - PEER DOESN'T BELONG TO THE GROUP"
        else:
            answer = "ERROR - GROUP DOESN'T EXIST"

    except IndexError:
        answer = "ERROR - INVALID REQUEST"

    return answer



def leaveGroup(groups, groupsLock, groupName, peerID):
    """remove the peer from the group"""
    groupsLock.acquire()

    groups[groupName].removePeer(peerID)

    groupsLock.release()

    answer = "OK - GROUP LEFT"
    return answer

def disconnectGroup(groups, groupsLock, groupName, peerID):
    """disconnect the peer from the group (active=False)"""
    groupsLock.acquire()

    groups[groupName].disconnectPeer(peerID)

    groupsLock.release()

    answer = "OK - GROUP DISCONNECTED"
    return answer

def peerExit(groups, groupsLock, peerID):
    """Disconnect the peer from all the synchronization groups in which is active"""

    groupsLock.acquire()

    for group in groups.values():
        if peerID in group.peersInGroup:
            if group.peersInGroup[peerID].active:
                group.disconnectPeer(peerID)

    groupsLock.release()


    answer = "OK - PEER DISCONNECTED"
    return answer

