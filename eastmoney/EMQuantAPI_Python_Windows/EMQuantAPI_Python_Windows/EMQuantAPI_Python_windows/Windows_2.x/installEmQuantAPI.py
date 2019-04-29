# -*- encoding:utf-8 -*-

__author__ = 'jiejie'

import sys
import os
def installEmQuantAPI():
    print "Start to install EmQuantAPI..."
    version = sys.version
    print "Current Python version:", version
    verNums = version.split()[0].split(".")
    ver = int(verNums[0]) + float(verNums[1])/10
    if ver < 2.6:
        print('Error: Python version must be >=2.6!')
        return

    currDir = os.path.split(os.path.realpath(__file__))[0]

    #get site-packages path
    packagepath = "."
    for x in sys.path:
        ix=x.find('site-packages')
        if( ix>=0 and x[ix:]=='site-packages'):
          packagepath=x
          break

    pthPath = packagepath + "\\EmQuantAPI.pth"
    pthFile = open(pthPath, "w")
    pthFile.writelines(currDir)
    pthFile.close()

    print "Success:", "EmQuantAPI installed."

installEmQuantAPI()
