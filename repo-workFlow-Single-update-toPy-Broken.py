
# coding: utf-8

# In[2]:


import keplerSettings as keplerSettings


# In[3]:


import findspark
findspark.init(keplerSettings.sparkHome)


# In[4]:


from astropy.io import fits


# In[5]:


#import astroprov
import sys
import datetime
import time
import collections
import subprocess

import numpy as np
import os

from astropy.table import Table
from astropy.table import Column
from astropy.io import ascii

import sqlite3
from pandas import DataFrame

import mysql.connector
from mysql.connector import Error
from mysql.connector import pooling

from pyspark.sql import Row
from pyspark.sql import SQLContext
from pyspark import SparkContext
from pyspark import SparkConf

#from sqlalchemy import create_engine
#from multiprocessing import Pool
#from multiprocessing.pool import ThreadPool
#from functools import partial
#from sqlalchemy import create_engine
#from astropy.visualization.mpl_normalize import ImageNormalize


# In[6]:


defaultDirectory = keplerSettings.sextractorDirectory


# In[16]:


os.environ['PYSPARK_SUBMIT_ARGS'] = '--jars '+ keplerSettings.mysqlSQLConnector+'  pyspark-shell'
config = SparkConf().setAll(keplerSettings.sparkConfig) # ("spark.sql.execution.arrow.enabled", "true")


# In[17]:


sc = SparkContext(appName='App',conf=config)
sqlContext = SQLContext(sc)


# In[18]:



mags = keplerSettings.magRangeSQLnaming
for mag in mags:
    dataframe_mysql = sqlContext.read.format("jdbc").option("url",  keplerSettings.databaseLoc).option("driver", "com.mysql.jdbc.Driver").option("dbtable", "starlist_{}".format(mag)).option("user", keplerSettings.databaseUsername).option("password", keplerSettings.databasePassword).load()
    dataframe_mysql.registerTempTable('starlist_{}'.format(mag))


# In[7]:


def innerJoin(tableName,totGross,totGrossOriginal,variableList,mag,baseNum,diffSize=1,xlength=keplerSettings.astroImageXlength,ylength=keplerSettings.astroImageYlength,weight=0.5):
    nsegs = keplerSettings.nsegs
    nperseg = keplerSettings.totalObjects/(nsegs**2)
    actualtTotObjects = nperseg*nsegs*nsegs
    #mag = variableList[6]
    temptableName = tableName[0:5]+tableName[-1]
    OGtemptableName = 'original'
    OGdf = sqlContext.sql("SELECT NUMBER, MAG_BEST, X_IMAGE, Y_IMAGE FROM {0} INNER JOIN starlist_{1} ON {0}.X_IMAGE BETWEEN starlist_{1}.X_POS_MIN AND starlist_{1}.X_POS_MAX AND {0}.Y_IMAGE BETWEEN starlist_{1}.Y_POS_MIN AND starlist_{1}.Y_POS_MAX".format(OGtemptableName,abs(mag)))
    OGdf.registerTempTable(OGtemptableName+'match')
    sqlContext.cacheTable(OGtemptableName+'match')
    
    OGtotNumDF = sqlContext.sql("SELECT * FROM {}".format(OGtemptableName))
    OGtotNumber = OGtotNumDF.count()
    
    df = sqlContext.sql("SELECT NUMBER, MAG_BEST, X_IMAGE, Y_IMAGE FROM {0} INNER JOIN starlist_{1} ON {0}.X_IMAGE BETWEEN starlist_{1}.X_POS_MIN AND starlist_{1}.X_POS_MAX AND {0}.Y_IMAGE BETWEEN starlist_{1}.Y_POS_MIN AND starlist_{1}.Y_POS_MAX".format(temptableName,abs(mag)))
    df.registerTempTable(temptableName+'match')
    sqlContext.cacheTable(temptableName+'match')
    totNumber = df.count()
    #print('tot',totNumber)
    
    xsegment = xlength/nsegs
    ysegment = ylength/nsegs
    
    accuracyScore = (float(OGtotNumber)/float(baseNum))
    #print('og',OGtotNumber,'base',baseNum,'tot',totNumber)
    completenessScore = 0
    #totSeg = []
    border = keplerSettings.border
    #df.write.format('jdbc').options(url='jdbc:mysql://localhost/Kepler',driver='com.mysql.jdbc.Driver',dbtable='result_{}'.format(tableName),user='mj1e16',password='[sqlT1G3R]').mode('append').save()
    for xsegs in range(nsegs):
        xmin = int(xsegs*xsegment)+border
        xmax = int(xmin+xsegment)+border
        for ysegs in range(nsegs):
            ymin = int(ysegs*ysegment)+border
            ymax = int(ymin+ysegment)+border
            
            OGdf = sqlContext.sql("SELECT NUMBER FROM {0} WHERE {0}.X_IMAGE BETWEEN {1} AND {2} AND {0}.Y_IMAGE BETWEEN {3} AND {4}".format(OGtemptableName+'match',xmin,xmax,ymin,ymax))
            OGnumber = OGdf.count()
            df = sqlContext.sql("SELECT NUMBER FROM {0} WHERE {0}.X_IMAGE BETWEEN {1} AND {2} AND {0}.Y_IMAGE BETWEEN {3} AND {4}".format(temptableName+'match',xmin,xmax,ymin,ymax))
            number = df.count()
            simulated = number-OGnumber
            if simulated > nperseg:
                simulated = nperseg 
            completenessScore +=  simulated #abs(simulated-62)
            
            variableList.append(simulated)
            
#             dftot = sqlContext.sql("SELECT NUMBER FROM {0} WHERE {0}.X_IMAGE BETWEEN {1} AND {2} AND {0}.Y_IMAGE BETWEEN {3} AND {4}".format(temptableName,xmin,xmax,ymin,ymax))
#             number = df.count()
#             #variableList.append(number)
#             totSeg.append(number)

            # need to create some place to write to

    
    
#    variableList.extend(totSeg)
    #astroprov.provcall([tableName,'starlist_{}'.format(abs(mag))],['result_{}'.format(tableName)],"innerJoin_Python2Python_SQ_tmpl.provn","innerJoin",provDir)
    compScore = 1. - (completenessScore/float(actualtTotObjects))
    #score = (weight*compScore) + ((1.-weight)*accuracyScore)
    #print(score,compScore,accuracyScore)
    sqlContext.uncacheTable(temptableName+'match')
    sqlContext.dropTempTable(temptableName+'match')
    sqlContext.uncacheTable(OGtemptableName+'match')
    sqlContext.dropTempTable(OGtemptableName+'match')
    sqlContext.uncacheTable(temptableName)
    sqlContext.dropTempTable(temptableName)
    sqlContext.uncacheTable(OGtemptableName)
    sqlContext.dropTempTable(OGtemptableName)
    variableList.append(totNumber)
    variableList.append(totGross)
    variableList.append(OGtotNumber)
    variableList.append(totGrossOriginal) 
    variableList.append(compScore)
    variableList.append(accuracyScore)
    variableTuple = tuple(variableList)
    #print(variableTuple)
    return [variableTuple]


def makeConfig(valList,tableName='table',defaultDir=defaultDirectory,attributeList=keplerSettings.sextractorAttributeList):
    
    with open(defaultDir+'/default.sex','r') as f:
        data  = f.read()
    for x in range(len(valList)):
        nameLoc = data.find(attributeList[x]) + len(attributeList[x])
        endLoc = data[nameLoc:].find('#') + nameLoc
        newData = data[:nameLoc] + ' '+str(valList[x])+' ' + data[endLoc:]
        data = newData
    
    cname = 'CATALOG_NAME'
    catName = 'test1.cat'
    confName = 'default_1.sex'
    nameLoc = data.find(cname) + len(cname)
    endLoc = data[nameLoc:].find('#') + nameLoc
    newData = data[:nameLoc] + ' ' +catName+ ' ' + data[endLoc:]
    data = newData

    cname = 'PARAMETERS_NAME'
    nameLoc = data.find(cname) + len(cname)
    endLoc = data[nameLoc:].find('#') + nameLoc
    newData = data[:nameLoc] + ' autodefault.param ' + data[endLoc:]
    
    #print(newData)
    with open(defaultDir+confName,'w') as f:
        f.write(newData)
    return(confName,tableName,catName)

def findObjects(confName,tableName,catName,defaultDir=defaultDirectory,imagename='/home/mj1e16/iraf/editedImage5000.fits',original='no',base='no'):
    
    os.chdir(defaultDir)
    subprocess.call(['sex',imagename,'-c',confName])
    assoc = Table.read(catName,format='ascii.sextractor')
    df = assoc.to_pandas()
    df2 = df[df['MAG_BEST'] != 99.0000]
    df_spark = sqlContext.createDataFrame(df2)
    temptableName = tableName[0:5]+tableName[-1]
    if original == 'yes':
        temptableName = 'original'
    if base == 'yes':
        temptableName = 'baseSettings'
    df_spark.registerTempTable(temptableName)
    totGross = df_spark.count()
    sqlContext.cacheTable(temptableName)

    return totGross

def alltogethernow(valList,tableName,IMAGE,variableList,originalImage,mag,atList,baseNum):
    Names = makeConfig(valList,tableName=tableName,attributeList=atList)
    totGrossOriginal = findObjects(Names[0],Names[1],Names[2],imagename=originalImage,original='yes')
    totGross = findObjects(Names[0],Names[1],Names[2],imagename=IMAGE) # confName tabName catname
    finalTuple = innerJoin(Names[1],totGross,totGrossOriginal,variableList,mag,baseNum)
    return finalTuple # named final tuple but actually [finaltuple,score]


# In[8]:


def hotpantsQuality(image):
    hdu = fits.open(image)
    imData = hdu[0].data
    imData = abs(imData)
    totVal = sum(imData)
    totVal = sum(totVal)
    return totVal


# In[9]:


valList = keplerSettings.sextractorValueList


# In[21]:


#valList = [np.linspace(1,10,1),np.linspace(1,9,2),['gauss_1.5_3x3.conv']] # for testing


# In[11]:


def evaluateImage(valList,simImage,OGImage,ccd,median,norm,minmag,baseNum,smallName='newRun',atList=keplerSettings.sextractorAttributeList,dbtabname='finalresultsTable'):
    
    finalTableTuples = []
    t0 = time.time()

    for x0 in range(len(valList[0])):
        for x1 in range(len(valList[1])):
                name = smallName+'_'+str(x0)+'_'+str(x1)+'_'
                for x2 in range(len(valList[2])):
                    variableList = [float(valList[0][x0]),float(valList[1][x1]),valList[2][x2],ccd,median,minmag,norm]
                    fullname = name+str(x2)
                    fullValList = [valList[0][x0],valList[1][x1],valList[2][x2]]
                    print(fullname)
                    try:
                        alltogethernowResults = alltogethernow(fullValList,tableName=fullname,IMAGE=simImage,variableList=variableList,originalImage=OGImage,mag=minmag,baseNum=baseNum,atList=atList)
                        finalTableTuples.append(alltogethernowResults[0])
                        #score = alltogethernowResults[1]
                    except RuntimeError:
                        with open('redos','a') as f:
                            bigString = simImage+','+str(fullname)+','+str(fullValList)
                            f.write(bigString)
                        print('Redo with valList = ',fullValList)
                        pass

    #print(finalTableTuples)
    rdd = sc.parallelize(finalTableTuples)
    kepler = rdd.map(lambda x: Row(detectThresh=x[0],detectMinarea=x[1],filterName=x[2],ccd=x[3],median=x[4],medianQuality=x[5],
                                   minmag=x[6], xy_0=int(x[7]),xy_1=int(x[8]),xy_2=int(x[9]),xy_3=int(x[10]),xy_4=int(x[11]),
                                   xy_5=int(x[12]),xy_6=int(x[13]),xy_7=int(x[14]),xy_8=int(x[15]),xy_9=int(x[16]),xy_10=int(x[17]),
                                   xy_11=int(x[18]),xy_12=int(x[19]),xy_13=int(x[20]),xy_14=int(x[21]),xy_15=int(x[22]),
                                   totNum=int(x[23]),totGross=int(x[24]),OGtot=int(x[25]),OGtotGross=int(x[26]),completenessScore=int(x[27]),accuracyScore=int(x[28])))

    schemaKepler = sqlContext.createDataFrame(kepler)
    #print('finalResults_{}_{}_{}'.format(ccd,median,minmag))
    #print(dbtabname)
    schemaKepler.write.format('jdbc').options(url=keplerSettings.databaseLoc,driver='com.mysql.jdbc.Driver',dbtable=dbtabname,user=keplerSettings.databaseUsername,password=keplerSettings.databasePassword).mode('append').save()
    
    print(time.time()-t0)


# In[23]:


# ccd = [44,63,79]
# median = [0,1,2]
# mags = np.linspace(-7,-1,7)

ccd = [44] #,63,79]
#ccd = keplerSettings.ccdExtensions
median = [1]
mags = keplerSettings.magRange


# In[13]:



# norms = []
# for inc,c in enumerate(ccd):
#     totVals = []
#     x =median
#     totVals.append(hotpantsQuality('/home/mj1e16/Simages/diff_{}_{}.fits'.format(c,x)))
#     norms.append([float(y/totVals[1]) for y in totVals])
# #print(norms)
# totVals = 
# norm = 


# In[85]:


#valList = [np.linspace(1,10,2),np.linspace(1,9,2),['gauss_1.5_3x3.conv']]


# In[24]:


### Make function to replace starlist
bestSettings = []
baseSettings = [valList[0][0],valList[1][0],valList[2][0]]
#starting = [4,4,14]
for inc,c in enumerate(ccd):
    for inmed,med in enumerate(median):
        ogim = keplerSettings.simulatedImageDirectory+'diff_{}_{}.fits'.format(c,med)
        baseNames = makeConfig(baseSettings,tableName='baseTable')
        baseNum = findObjects(baseNames[0],baseNames[1],baseNames[2],imagename=ogim,base='yes')
        norm = 1.0
        for mag in mags:
            sqlContext.cacheTable('starlist_{}'.format(abs(mag)))            
            imName = keplerSettings.simulatedImageDirectory+'diff_{}_{}{}_alt.fits'.format(c,med,mag)
            tabName = 'bigSimsTest2_{}_{}_{}'.format(c,med,abs(mag))
            evaluateImage(valList,imName,ogim,'ccd_{}'.format(c),'median_{}'.format(med),norm,mag,baseNum,smallName=tabName,dbtabname='results'+tabName)
            sqlContext.uncacheTable('starlist_{}'.format(abs(mag)))
            #starting = bestSettings[-1]


# In[ ]:





# In[ ]:





# In[ ]:




