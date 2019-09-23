import datetime 
import os
import subprocess

date = str(datetime.datetime.now())
day = date[0:10]
provstart = '/home/mj1e16/keplerPhotometry/provDump/'+day


subprocess.call(['mkdir',provstart])
subprocess.call(['mkdir',provstart+'/image'+str(0)])

#os.mkdir(provstart+'/image'+str(0))
#
#for x in range(3):
#    try:
#        print(provstart+'/image'+str(x))#
#	print('sucess')
 #       os.mkdir(provstart+'/image'+str(x))
 #   except OSError:
#	print('fail')
#        print(provstart+'/image'+str(x))
#        pass

