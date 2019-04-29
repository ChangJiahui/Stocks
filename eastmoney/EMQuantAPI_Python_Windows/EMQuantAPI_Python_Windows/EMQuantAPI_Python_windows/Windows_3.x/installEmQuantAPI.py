__author__ = 'weijie'

import sys
import os

def installEmQuantAPI():
    print("Start to install EmQuantAPI...")
    version = sys.version
    print("Current Python version:", version)

    verNums = version.split()[0].split(".")
    ver = int(verNums[0]) + float(verNums[1])/10

    if(ver < 3.0):
        print("Error: Python version must be 3.x")
        return

    currDir = os.path.split(os.path.realpath(__file__))[0]
    
    packagepath = "."

    for x in sys.path:
        xx = x.find("site-packages")
        if(xx>=0and x[xx:]=="site-packages"):
            packagepath = x
            break

    pthPath = packagepath + "\\EmQuantAPI.pth"
    pthFile = open(pthPath, "w")
    pthFile.writelines(currDir)
    pthFile.close()
    
    print("Success:", "EmQuantAPI installed.")
    
installEmQuantAPI()
