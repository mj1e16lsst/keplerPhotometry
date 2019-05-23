
# coding: utf-8

# In[ ]:


import findspark
#findspark.find()
findspark.init('/home/mj1e16/miniconda2/lib/python2.7/site-packages/pyspark')


# In[ ]:


import astroprov
import numpy as np
import os

from astropy.visualization.mpl_normalize import ImageNormalize
from astropy.table import Table
from astropy.table import Column

import collections
import subprocess

import time
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool

from functools import partial

from astropy.io import ascii
from sqlalchemy import create_engine
import sqlite3
import mysql.connector
from pandas import DataFrame

import mysql.connector
from mysql.connector import Error
from mysql.connector import pooling

from pyspark.sql import SQLContext
from pyspark import SparkContext
from pyspark import SparkConf
import datetime


# In[ ]:


os.environ['PYSPARK_SUBMIT_ARGS'] = '--jars /home/mj1e16/miniconda2/lib/python2.7/site-packages/pyspark/mysql-connector-java_8.0.16-1ubuntu16.04_all/usr/share/java/mysql-connector-java-8.0.16.jar  pyspark-shell'


# In[ ]:


config = SparkConf().setAll([('spark.executor.cores', '6'),('spark.cores.max', '6'),('spark.driver.memory','8g'),('spark.executor.memory', '8g')])


# In[ ]:


sc = SparkContext(appName='App',conf=config)
sqlContext = SQLContext(sc)


# In[ ]:


dataframe_mysql = sqlContext.read.format("jdbc").option("url", "jdbc:mysql://localhost/Kepler").option("driver", "com.mysql.jdbc.Driver").option("dbtable", "starlist").option("user", "mj1e16").option("password", "[sqlT1G3R]").load()
dataframe_mysql.registerTempTable('starlist')


# In[ ]:


def restartSpark(sc):
    sc.stop()
    os.environ['PYSPARK_SUBMIT_ARGS'] = '--jars /home/mj1e16/miniconda2/lib/python2.7/site-packages/pyspark/mysql-connector-java_8.0.16-1ubuntu16.04_all/usr/share/java/mysql-connector-java-8.0.16.jar  pyspark-shell'
    config = SparkConf().setAll([('spark.executor.cores', '6'),('spark.cores.max', '6'),('spark.driver.memory','8g'),('spark.executor.memory', '8g')])
    sc = SparkContext(appName='App',conf=config)
    sqlContext = SQLContext(sc)
    dataframe_mysql = sqlContext.read.format("jdbc").option("url", "jdbc:mysql://localhost/Kepler").option("driver", "com.mysql.jdbc.Driver").option("dbtable", "starlist").option("user", "mj1e16").option("password", "[sqlT1G3R]").load()
    dataframe_mysql.registerTempTable('starlist')


# In[ ]:


def differenceImage(image1,image2,outName,provDir,verbosity=0):
 
    astroprov.provcall([image1,image2],[outName],"differenceImage_Python2Hotpants_SQ_tmpl.provn","differenceImage",provDir)
#     output = 'diffImage.fits'
#     os.chdir('/data/mj1e16/kepler/hotpants-master')# what directory?
#     subprocess.call(['./hotpants','-inim',image1,'-tmplin',image2,'-outim',outName,'v',str(verbosity)])
    return(outName)


# In[ ]:


def addStars(starlist,alteredImage,provDir):
    #pretend the function is here and record the provnenance
    astroprov.provcall([alteredImage,starlist],['alteredImage.fits'],"addStars_Python2IRAF_SQ_tmpl.provn","addStars",provDir)
    return('alteredImage.fits')


# In[ ]:


def innerJoin(tableName,provDir,diffSize=1):
    temptableName = tableName[0:5]+tableName[-1]
    df = sqlContext.sql("SELECT NUMBER, EXT_NUMBER, FLUX_ISO, FLUXERR_ISO, BACKGROUND, THRESHOLD, FLUX_MAX, XPEAK_IMAGE, YPEAK_IMAGE,  X_IMAGE, Y_IMAGE, FWHM_IMAGE, ELLIPTICITY FROM {} INNER JOIN starlist ON {}.X_IMAGE BETWEEN starlist.X_POS_MIN AND starlist.X_POS_MAX AND {}.Y_IMAGE BETWEEN starlist.Y_POS_MIN AND starlist.Y_POS_MAX".format(temptableName,temptableName,temptableName))
    df.write.format('jdbc').options(url='jdbc:mysql://localhost/Kepler',driver='com.mysql.jdbc.Driver',dbtable='result_{}'.format(tableName),user='mj1e16',password='[sqlT1G3R]').mode('append').save()
#     a = df.count()
#     print(a)
    sqlContext.dropTempTable(temptableName)
    astroprov.provcall([tableName,'starlist'],['result_{}'.format(tableName)],"innerJoin_Python2Python_SQ_tmpl.provn","innerJoin",provDir)



# In[ ]:


def makeConfig(valList,provDir,tableName='table',defaultDir='/home/mj1e16/sextractor/sextractor-master/config/',attributeList=['DETECT_THRESH','DETECT_MINAREA','BACK_TYPE','BACK_VALUE','BACK_FILTERSIZE','BACK_SIZE']):
    
    #workAroundList = [16,32,64,128,256,512]
    workAroundList = [1,3,5,7,9,11]
    ident = workAroundList.index(valList[-1])
    tableName = tableName[ident] # could just return a letter?
    with open(defaultDir+'/default.sex','r') as f:
        data  = f.read()
    
    catLocFinder = 'CATALOG_NAME'
    catname = 'test'+str(ident)+'.cat'
    nameLoc = data.find(catLocFinder) + len(catLocFinder)
    endLoc = data[nameLoc:].find('#') + nameLoc
    newData = data[:nameLoc] + ' '+catname+' ' + data[endLoc:]
    data = newData 
        
    for x in range(len(valList)):
        nameLoc = data.find(attributeList[x]) + len(attributeList[x])
        endLoc = data[nameLoc:].find('#') + nameLoc
        newData = data[:nameLoc] + ' '+str(valList[x])+' ' + data[endLoc:]
        data = newData    
    
    
    confName = 'default_'+str(ident)+'.sex'
    with open(defaultDir+confName,'w') as f:
        f.write(data)
    astroprov.provcall(valList,[confName],"makeConfig_Python2Python_SQ_tmpl.provn","makeConfig",provDir)
    return(confName,tableName,catname)


# In[ ]:


def findObjects(confName,tableName,catName,provDir,defaultDir='/home/mj1e16/sextractor/sextractor-master/config/',imagename='/home/mj1e16/iraf/editedImage5000.fits'):
    
    astroprov.provcall([confName,'/home/mj1e16/iraf/editedImage5000.fits'],[tableName],"findObjects_Python2DaoStarfidner_SQ_tmpl.provn","findObjects",provDir)

    os.chdir(defaultDir)
    subprocess.call(['sex',imagename,'-c',confName])
    assoc = Table.read(catName,format='ascii.sextractor')
    df = assoc.to_pandas()
    df_spark = sqlContext.createDataFrame(df)
    temptableName = tableName[0:5]+tableName[-1]
    #print(temptableName)
    df_spark.registerTempTable(temptableName)


# In[ ]:


def alltogethernow(valList,tableName,IMAGE,provDir):
    Names = makeConfig(valList,provDir,tableName=tableName)
    findObjects(Names[0],Names[1],Names[2],provDir,imagename=IMAGE) # confName tabName catname
    innerJoin(Names[1],provDir)


# In[ ]:




atList = ['DETECT_THRESH','DETECT_MINAREA','BACK_SIZE','BACK_FILTERSIZE']

#valList = [np.linspace(1.5,6,8),np.linspace(5,14,10),['AUTO'],np.linspace(1,10,10),[16,32,64,128,256,512]]
#astro = [(1,10,1),(1,9,1),[auto],(values from 7.2),(8,128,8)]
valList = [np.linspace(1,10,10),np.linspace(1,9,9),np.linspace(8,128,16),[1,3,5,7,9,11]] # astro start


p = ThreadPool(6)
t0 = time.time()

date = str(datetime.datetime.now())
day = date[0:10]
provstart = '/home/mj1e16/keplerPhotometry/provDump/'+day


for x in range(3):
     try:
         os.mkdir(provstart+'/image'+str(x))
     except OSError:
         print(provstart+'/image'+str(x))
         pass

#os.mkdir(provstart+'/image2')
#os.mkdir(provstart+'/image3')

imageDiff = ['/home/mj1e16/iraf/kplr2009114174833_ffi-cal_TEMPLATE.fits']#,'/home/mj1e16/iraf/kplr2009114174833_ffi-cal_TEMPLATE_PLUS5000.fits']
imageTem = ['/home/mj1e16/iraf/kplr2010019225502_ffi-cal_DIFF_PLUS5000.fits'] #,'/home/mj1e16/iraf/kplr2010019225502_ffi-cal_DIFF.fits']
for imageNumber in range(1):
    if imageNumber == 0:
        provDir = provstart+'/image1/'
        addStars('starlist',imageTem[0],provDir)
        imageName = differenceImage(imageTem[0],imageDiff[0],'/home/mj1e16/iraf/simImage1.fits',provDir)
        smallName = 'spark1'
    if imageNumber == 1:
        provDir = provstart+'/image2/'
        addStars('starlist',imageTem[0],provDir)
        imageName = differenceImage(imageDiff[0],imageTem[0],'/home/mj1e16/iraf/simImage2.fits',provDir)
        smallName = 'spark2'
    if imageNumber == 2:
        provDir = provstart+'/image3/'
        imageName = '/home/mj1e16/iraf/simpleDiffImagePLUS5000.fits'
        astroprov.provcall(['/home/mj1e16/iraf/kplr2010019225502_ffi-cal_DIFF.fits','/home/mj1e16/iraf/kplr2009114174833_ffi-cal_TEMPLATE.fits'],[imageName],"differenceImage_Python2Hotpants_SQ_tmpl.provn","differenceImage",provDir)
        addStars('starlist',imageName,provDir)
        smallName = 'spark3'
    for x0 in range(7,len(valList[0])):
        for x1 in range(len(valList[1])):
                for x2 in range(len(valList[2])):
                    name = smallName+'_'+str(x0)+'_'+str(x1)+'_'+str(x2)+'_'
                    fullname = [name]*len(valList[3])
                    fullValList = []
                    for x3 in range(len(valList[3])):
                        fullname[x3] += str(x3)
                        print(fullname[x3])
                        fullValList.append([valList[0][x0],valList[1][x1],valList[2][x2],valList[3][x3]])

                        #alltogethernow(fullValList[x4],fullname,imageName,provDir)
                    try:
                    	p.map(partial(alltogethernow,tableName=fullname,IMAGE=imageName,provDir=provDir),fullValList)
                    except RuntimeError:
			print('Redo with valList = ',fullValList)
			pass

#def alltogethernow(valList,tableName,IMAGE,provDir):

print(time.time()-t0)


# In[ ]:




