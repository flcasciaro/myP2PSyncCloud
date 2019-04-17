import sys

from PyQt5.QtWidgets import *

import peerCore


class myP2PSyncCloud(QMainWindow):

    def __init__(self):
        super().__init__()
        """Window properties definition"""
        self.title = "myP2PSyncCloud"
        self.left = 300
        self.top = 50
        self.width = 500
        self.height = 500

        """Window main structure definition"""
        self.splitter = QSplitter()
        self.groupManager = QFrame()
        self.fileManager = QFrame()

        """Define a vertical box layout for the two main parts of the window"""
        self.groupManagerLayout = QVBoxLayout()
        self.fileManagerLayout = QVBoxLayout()

        """Declaration of UI object in the groupManager frame"""
        self.peerLabel = QLabel()
        self.serverLabel = QLabel()
        """self.serverButton = QPushButton("CHANGE SERVER")
        self.groupNameCreate = QTextEdit("Enter group name")
        self.tokenRWCreate = QTextEdit("Enter token")
        self.tokenROCreate = QTextEdit("Enter token")
        self.createButton = QPushButton("CREATE")
        self.groupNameRestore = QTextEdit("Enter group name")
        self.restoreButton = QPushButton("RESTORE")
        self.groupNameJoin = QTextEdit("Enter group name")
        self.tokenJoin = QTextEdit("Enter token")
        self.joinButton = QPushButton("RESTORE")"""
        self.activeGroupLabel = QLabel("List of ACTIVE groups")
        self.activeGroupList = QListWidget()
        self.otherGroupLabel = QLabel("List of ACTIVE groups")
        self.otherGroupList = QListWidget()

        """Declaration of UI object in the fileManager frame"""
        self.fileLabel = QLabel("FILE MANAGER")
        self.fileButton = QPushButton("SYNC")

        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setCentralWidget(self.splitter)

        self.splitter.addWidget(self.groupManager)
        self.splitter.addWidget(self.fileManager)
        """self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 5)"""

        self.groupManager.setLineWidth(3)
        self.fileManager.setLineWidth(3)
        self.groupManager.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.fileManager.setFrameStyle(QFrame.Box | QFrame.Raised)

        self.groupManager.setLayout(self.groupManagerLayout)
        self.fileManager.setLayout(self.fileManagerLayout)

        self.groupManagerLayout.addWidget(self.peerLabel)
        self.groupManagerLayout.addWidget(self.serverLabel)
        self.groupManagerLayout.addSpacing(30)
        self.groupManagerLayout.addWidget(self.activeGroupLabel)
        self.groupManagerLayout.addWidget(self.activeGroupList)
        self.groupManagerLayout.addSpacing(30)
        self.groupManagerLayout.addWidget(self.otherGroupLabel)
        self.groupManagerLayout.addWidget(self.otherGroupList)

        self.fileManagerLayout.addWidget(self.fileLabel)
        self.fileManagerLayout.addWidget(self.fileButton)

        success = peerInitialization()

        self.peerLabel.setText("Personal peerID is {}".format(peerCore.peerID))
        self.serverLabel.setText("Connected to server at {}:{}".format(peerCore.serverIP, peerCore.serverPort))

        self.activeGroupList.setToolTip("Double click on a group in order to see files")
        self.otherGroupList.setToolTip("Double click on a group in order to join or restore it")

        groupList = ["ciao", "sono", "pablo"]
        for group in groupList:
            self.activeGroupList.addItem(group)
        # self.activeGroupList.addScrollBarWidget()

        self.show()

        if not success:
            """Create dialog box in order to set server coordinates"""
            ok = False
            while not ok:
                coordinates, ok = QInputDialog.getText(self, 'Server coordinates',
                                                       'Enter Server IP Address and Server Port\nUse the format: serverIP:ServerPort')

            peerCore.setServerCoordinates(coordinates)
            self.serverLabel.setText("Connected to server at {}:{}".format(peerCore.serverIP, peerCore.serverPort))

        # try to reach the server


def peerInitialization():
    peerCore.setPeerID()
    found = peerCore.findServer()
    if found:
        return True
    else:
        return False


if __name__ == '__main__':
    app = QApplication([])
    ex = myP2PSyncCloud()
    sys.exit(app.exec_())
