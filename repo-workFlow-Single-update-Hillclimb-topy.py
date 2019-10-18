
# coding: utf-8

# In[11]:


import keplerSettings as keplerSettings


# In[12]:


import findspark
findspark.init(keplerSettings.sparkHome)


# In[13]:


from astropy.io import fits


# In[14]:


#import astroprov
import sys
import datetime
import time
import collections
import subprocess
import random

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


# In[15]:


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


# In[19]:


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
    completenessScore = 0.
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
            if simulated >  nperseg:
                simulated =  nperseg 
            completenessScore +=  simulated #abs(simulated-62)
            
            variableList.append(simulated)
            
#             dftot = sqlContext.sql("SELECT NUMBER FROM {0} WHERE {0}.X_IMAGE BETWEEN {1} AND {2} AND {0}.Y_IMAGE BETWEEN {3} AND {4}".format(temptableName,xmin,xmax,ymin,ymax))
#             number = df.count()
#             #variableList.append(number)
#             totSeg.append(number)

            # need to create some place to write to

    
    
#    variableList.extend(totSeg)
    #astroprov.provcall([tableName,'starlist_{}'.format(abs(mag))],['result_{}'.format(tableName)],"innerJoin_Python2Python_SQ_tmpl.provn","innerJoin",provDir)
    #compScore = 1. - (completenessScore/992.)
    compScore = 1. - (float(completenessScore)/float(actualtTotObjects))

    score = (weight*compScore) + ((1.-weight)*accuracyScore)
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
    variableList.append(score)
    variableList.append(compScore)
    variableList.append(accuracyScore)
    variableTuple = tuple(variableList)
    #print(variableTuple)
    return [variableTuple,score]


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

def alltogethernow(valList,tableName,IMAGE,variableList,originalImage,mag,atList,baseNum,weight=0.5):
    Names = makeConfig(valList,tableName=tableName,attributeList=atList)
    totGrossOriginal = findObjects(Names[0],Names[1],Names[2],imagename=originalImage,original='yes')
    totGross = findObjects(Names[0],Names[1],Names[2],imagename=IMAGE) # confName tabName catname
    finalTuple = innerJoin(Names[1],totGross,totGrossOriginal,variableList,mag,baseNum,weight=weight)
    return finalTuple # named final tuple but actually [finaltuple,score]


# In[20]:


def hotpantsQuality(image):
    hdu = fits.open(image)
    imData = hdu[0].data
    imData = abs(imData)
    totVal = sum(imData)
    totVal = sum(totVal)
    return totVal


# In[21]:


valList = keplerSettings.sextractorValueList


# In[22]:


def evaluateImage(valList,simImage,OGImage,ccd,median,norm,minmag,smallName='newRun',atList=keplerSettings.sextractorAttributeList,dbtabname='finalresultsTable'):
    
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
                        alltogethernowResults = alltogethernow(fullValList,tableName=fullname,IMAGE=simImage,variableList=variableList,originalImage=OGImage,mag=minmag,atList=atList,weight=weight)
                        finalTableTuples.append(alltogethernowResults[0])
                        score = alltogethernowResults[1]
                    except RuntimeError:
                        with open('redos','a') as f:
                            bigString = simImage+','+str(fullname)+','+str(fullValList)
                            f.write(bigString)
                        print('Redo with valList = ',fullValList)
                        pass

    print(finalTableTuples)
    rdd = sc.parallelize(finalTableTuples)
    kepler = rdd.map(lambda x: Row(detectThresh=x[0],detectMinarea=x[1],filterName=x[2],ccd=x[3],median=x[4],medianQuality=x[5],
                                   minmag=x[6], xy_0=int(x[7]),xy_1=int(x[8]),xy_2=int(x[9]),xy_3=int(x[10]),xy_4=int(x[11]),
                                   xy_5=int(x[12]),xy_6=int(x[13]),xy_7=int(x[14]),xy_8=int(x[15]),xy_9=int(x[16]),xy_10=int(x[17]),
                                   xy_11=int(x[18]),xy_12=int(x[19]),xy_13=int(x[20]),xy_14=int(x[21]),xy_15=int(x[22]),
                                   totNum=int(x[23]),totGross=int(x[24]),OGtot=int(x[25]),OGtotGross=int(x[26]),score=int(x[27])))

    schemaKepler = sqlContext.createDataFrame(kepler)
    #print('finalResults_{}_{}_{}'.format(ccd,median,minmag))
    schemaKepler.write.format('jdbc').options(url='jdbc:mysql://localhost/Kepler',driver='com.mysql.jdbc.Driver',dbtable='finalResultsNewRun_{}_{}_{}'.format(ccd,median,abs(minmag)),user='mj1e16',password='[sqlT1G3R]').mode('append').save()
    
    print(time.time()-t0)


# In[23]:


def oneSettingEvaluate(valList,simImage,OGImage,ccd,median,norm,minmag,baseNum,smallName='newRun',starting=[0,0,0],atList=keplerSettings.sextractorAttributeList,weight=0.5):
    
    fullname = smallName+'_'+str(starting[0])+'_'+str(starting[1])+'_'+str(starting[2])               
    variableList = [float(valList[0][starting[0]]),float(valList[1][starting[1]]),valList[2][starting[2]],ccd,median,minmag,norm]
    fullValList = [valList[0][starting[0]],valList[1][starting[1]],valList[2][starting[2]]]
    print(fullname)
    print(starting)
    try:
        alltogethernowResults = alltogethernow(fullValList,tableName=fullname,IMAGE=simImage,variableList=variableList,originalImage=OGImage,mag=minmag,atList=atList,baseNum=baseNum,weight=weight)
        finalTableTuples = alltogethernowResults[0]
        baseScore = alltogethernowResults[1]
    except RuntimeError:
        with open('/home/mj1e16/keplerPhotometry/redos.txt','a') as f:
            bigString = simImage+','+str(fullname)+','+str(fullValList)
            f.write(bigString)
            basescore = -1
        print('Redo with valList = ',fullValList)
        pass
    print(baseScore)
    return [finalTableTuples,baseScore]


# In[24]:


# def evaluateImageHillClimbVersionOne(valList,simImage,OGImage,ccd,median,norm,minmag,smallName='newRun',atList=['DETECT_THRESH','DETECT_MINAREA','FILTER_NAME'],starting=[0,0,0]):
    
#     finalTableTuples = []
#     t0 = time.time()
#     scores = []
    
#     for loop in range(2):
#         for x in range(len(valList)):
#             scorePerVal = []
#             for y in range(len(valList[x])):
#                 starting[x] = y
#                 fullname = smallName+'_'+str(starting[0])+'_'+str(starting[1])+'_'+str(starting[2])                
#                 variableList = [float(valList[0][starting[0]]),float(valList[1][starting[1]]),valList[2][starting[2]],ccd,median,minmag,norm]
#                 fullValList = [valList[0][starting[0]],valList[1][starting[1]],valList[2][starting[2]]]
#                 print(starting)
#                 print(fullname)
#                 try:
#                     alltogethernowResults = alltogethernow(fullValList,tableName=fullname,IMAGE=simImage,variableList=variableList,originalImage=OGImage,mag=minmag,atList=atList)
#                     finalTableTuples.append(alltogethernowResults[0])
#                     scorePerVal.append(alltogethernowResults[1])
#                 except RuntimeError:
#                     with open('redos','a') as f:
#                         bigString = simImage+','+str(fullname)+','+str(fullValList)
#                         f.write(bigString)
#                         scorePerVal.append(-1)
#                     print('Redo with valList = ',fullValList)
#                     pass
#             goodScores = [sco for sco in scorePerVal if x >= 0]
#             best = scorePerVal.index(min(goodScores))
#             starting[x] = best

#     print(finalTableTuples)
#     rdd = sc.parallelize(finalTableTuples)
#     kepler = rdd.map(lambda x: Row(detectThresh=x[0],detectMinarea=x[1],filterName=x[2],ccd=x[3],median=x[4],medianQuality=x[5],
#                                    minmag=x[6], xy_0=int(x[7]),xy_1=int(x[8]),xy_2=int(x[9]),xy_3=int(x[10]),xy_4=int(x[12]),
#                                    xy_5=int(x[12]),xy_6=int(x[13]),xy_7=int(x[14]),xy_8=int(x[15]),xy_9=int(x[16]),xy_10=int(x[17]),
#                                    xy_11=int(x[18]),xy_12=int(x[19]),xy_13=int(x[20]),xy_14=int(x[21]),xy_15=int(x[22]),totNum=int(x[23]),totGross=int(x[24]),OGtotGross=int(x[25])))

#     schemaKepler = sqlContext.createDataFrame(kepler)
#     #print('finalResults_{}_{}_{}'.format(ccd,median,minmag))
#     schemaKepler.write.format('jdbc').options(url='jdbc:mysql://localhost/Kepler',driver='com.mysql.jdbc.Driver',dbtable='finalResultsNewRun_{}_{}_{}'.format(ccd,median,abs(minmag)),user='mj1e16',password='[sqlT1G3R]').mode('append').save()
    
#     print(time.time()-t0)
#     return starting


# In[25]:


# def evaluateImageHillClimbVersionOne(valList,simImage,OGImage,ccd,median,norm,minmag,smallName='newRun',atList=['DETECT_THRESH','DETECT_MINAREA','FILTER_NAME'],starting=[0,0,0]):
    
#     finalTableTuples = []
#     t0 = time.time()
#     scores = []
    
#     startingBest = 10**10
#     best = 10**9
    
#     while startingBest > best:
#         startingBest = best
#         for x in range(len(valList)):
#             scorePerVal = []
#             for y in range(len(valList[x])):
#                 starting[x] = y
#                 baseEvaluate = oneSettingEvaluate(valList,simImage,OGImage,ccd,median,norm,minmag,smallName=smallName,starting=starting,atList=atList)

#                 finalTableTuples.append(baseEvaluate[0])
#                 scorePerVal.append(baseEvaluate[1])

#             goodScores = [sco for sco in scorePerVal if x >= 0]
#             best = scorePerVal.index(min(goodScores))
#             bestList = [i for i, val in enumerate(goodScores) if val == min(goodScores)]
#             if len(bestList) == 1:
#                 best = bestList[0]
#             else:
#                 best = int(np.median(bestList))
#             starting[x] = best
#             print(scorePerVal)

#     print(finalTableTuples)
    
#     rdd = sc.parallelize(finalTableTuples)
#     kepler = rdd.map(lambda x: Row(detectThresh=x[0],detectMinarea=x[1],filterName=x[2],ccd=x[3],median=x[4],medianQuality=x[5],
#                                    minmag=x[6], xy_0=int(x[7]),xy_1=int(x[8]),xy_2=int(x[9]),xy_3=int(x[10]),xy_4=int(x[11]),
#                                    xy_5=int(x[12]),xy_6=int(x[13]),xy_7=int(x[14]),xy_8=int(x[15]),xy_9=int(x[16]),xy_10=int(x[17]),
#                                    xy_11=int(x[18]),xy_12=int(x[19]),xy_13=int(x[20]),xy_14=int(x[21]),xy_15=int(x[22]),
#                                    totNum=int(x[23]),totGross=int(x[24]),OGtot=int(x[25]),OGtotGross=int(x[26]),score=int(x[27])))

#     schemaKepler = sqlContext.createDataFrame(kepler)
#     #print('finalResults_{}_{}_{}'.format(ccd,median,minmag))
#     schemaKepler.write.format('jdbc').options(url='jdbc:mysql://localhost/Kepler',driver='com.mysql.jdbc.Driver',dbtable='finalResultsSimpleLoop_{}_{}_{}'.format(ccd,median,abs(minmag)),user='mj1e16',password='[sqlT1G3R]').mode('append').save()
    
#     print(time.time()-t0)
#     return starting


# In[26]:


def evaluateImageHillClimbVersionTwo(valList,simImage,OGImage,ccd,median,norm,minmag,baseNum,smallName='newRun',starting=[0,0,0],atList=keplerSettings.sextractorAttributeList,dbtabname='finalresultsTable',weight=0.5):
    
    finalTableTuples = []
    t0 = time.time()
    scores = []
    
    baseEvaluate = oneSettingEvaluate(valList,simImage,OGImage,ccd,median,norm,minmag,baseNum,smallName=smallName,starting=starting,atList=atList,weight=weight)
    finalTableTuples.append(baseEvaluate[0])
    baseScore = baseEvaluate[1]
    startScore = baseScore + 1
    
    plusMinus = [-1,1]
    while baseScore < startScore:
        startScore = baseScore
        for x in range(len(valList)):
            for y in plusMinus:
                delta = -1
                while delta < 0:
                    minus = [z for z in starting]
                    minus[x] += y
                    if 0 < minus[x] < len(valList[x]):
                        minusEvaluate = oneSettingEvaluate(valList,simImage,OGImage,ccd,median,norm,minmag,baseNum,smallName=smallName,starting=minus,atList=atList,weight=weight)
                        finalTableTuples.append(minusEvaluate[0])
                        minusScore = minusEvaluate[1]

                        delta = minusScore - baseScore
                        print('delta',delta,'starting',minus)
                        randomVals = [random.randint(0,len(valList[0])-1),random.randint(0,len(valList[1])-1),random.randint(0,len(valList[2])-1)]
                        randomEvaluate = oneSettingEvaluate(valList,simImage,OGImage,ccd,median,norm,minmag,baseNum,smallName=smallName,starting=randomVals,atList=atList,weight=weight)
                        finalTableTuples.append(randomEvaluate[0])
                        randomScore = randomEvaluate[1]

                        if randomScore < baseScore:
                            starting = randomVals
                            delta = randomScore - baseScore
                            baseScore = randomScore

                        elif minusScore < baseScore:
                            starting = minus
                            baseScore = minusScore
                    else:
                        break
                
                

    print(finalTableTuples)
    print(baseScore)
    print(starting)
    print(dbtabname)
    rdd = sc.parallelize(finalTableTuples)
    kepler = rdd.map(lambda x: Row(detectThresh=x[0],detectMinarea=x[1],filterName=x[2],ccd=x[3],median=x[4],medianQuality=x[5],
                                   minmag=x[6], xy_0=int(x[7]),xy_1=int(x[8]),xy_2=int(x[9]),xy_3=int(x[10]),xy_4=int(x[11]),
                                   xy_5=int(x[12]),xy_6=int(x[13]),xy_7=int(x[14]),xy_8=int(x[15]),xy_9=int(x[16]),xy_10=int(x[17]),
                                   xy_11=int(x[18]),xy_12=int(x[19]),xy_13=int(x[20]),xy_14=int(x[21]),xy_15=int(x[22]),
                                   totNum=int(x[23]),totGross=int(x[24]),OGtot=int(x[25]),OGtotGross=int(x[26]),score=x[27],
                                   completeness=x[28],accuracy=x[29]))

    schemaKepler = sqlContext.createDataFrame(kepler)
    #print('finalResults_{}_{}_{}'.format(ccd,median,minmag))
    schemaKepler.write.format('jdbc').options(url=keplerSettings.databaseLoc,driver='com.mysql.jdbc.Driver',dbtable=dbtabname,user=keplerSettings.databaseUsername,password=keplerSettings.databasePassword).mode('append').save()
    
    print(time.time()-t0)
    return starting


# In[27]:


ccd = keplerSettings.ccdExtensions
median = [1]
mags = keplerSettings.magRange


# In[28]:



# (lambda x: Row(detectThresh=x[0],detectMinarea=x[1],filterName=x[2],ccd=x[3],median=x[4],medianQuality=x[5],
#                                    minmag=x[6], xy_0=int(x[7]),xy_1=int(x[8]),xy_2=int(x[9]),xy_3=int(x[10]),xy_4=int(x[11]),
#                                    xy_5=int(x[12]),xy_6=int(x[13]),xy_7=int(x[14]),xy_8=int(x[15]),xy_9=int(x[16]),xy_10=int(x[17]),
#                                    xy_11=int(x[18]),xy_12=int(x[19]),xy_13=int(x[20]),xy_14=int(x[21]),xy_15=int(x[22]),
#                                    totNum=int(x[23]),totGross=int(x[24]),OGtot=int(x[25]),OGtotGross=int(x[26]),completenessScore=x[27],accuracyScore=x[28]))


# In[34]:


#bestSettings = []
baseSettings = [valList[0][0],valList[1][0],valList[2][0]]

c = ccd[0]
med = median[0]
norm = 1.0
ogim = keplerSettings.simulatedImageDirectory+'diff_{}_{}.fits'.format(c,med)
#weight = keplerSettings.Weight
#starting = [4,4,14]

# baseNames = makeConfig(baseSettings,tableName='baseTable')
# baseNum = findObjects(baseNames[0],baseNames[1],baseNames[2],imagename=ogim,base='yes')
startRanges = [[0,0,0],[-1,-1,-1],[random.randint(0,len(valList[0])),random.randint(0,len(valList[1])),random.randint(0,len(valList[2]))],[8,10,7]] 
startNames= ['min','max','random','chosen']
baseNames = makeConfig(baseSettings,tableName='baseTable')
baseNums = []
for mag in mags:
    baseNums.append(findObjects(baseNames[0],baseNames[1],baseNames[2],imagename=ogim,base='yes'))

#bestSetMonte = []
for monte in range(10):
    #bestSetStart = []
    for starting in startRanges:
        startname = startNames[startRanges.index(starting)]
        #bestsetWeight = []
        for w in range(1,9):#1,9
            weight = w/10.
            bestSettings = []
            for mag in mags:    
                baseNum = baseNums[mags.index(mag)]
                print(baseNum)
    #                 baseNames = makeConfig(baseSettings,tableName='baseTable')
    #                 baseNum = findObjects(baseNames[0],baseNames[1],baseNames[2],imagename=ogim,base='yes')
                sqlContext.cacheTable('starlist_{}'.format(abs(mag)))
                imName = keplerSettings.simulatedImageDirectory+'diff_{}_{}{}_alt.fits'.format(c,med,mag)
                tabName = keplerSettings.databaseTableName+'Final_{}_{}_{}_{}_{}_{}'.format(c,med,abs(mag),w,startname,monte)
                bestSettings.append(evaluateImageHillClimbVersionTwo(valList,imName,ogim,'ccd_{}'.format(c),'median_{}'.format(med),norm,mag,baseNum,smallName=tabName,starting=starting,weight=weight,dbtabname=tabName))
                sqlContext.uncacheTable('starlist_{}'.format(abs(mag)))
                #starting = bestSettings[-1]
 #           bestsetWeight.append(bestSettings)
#        bestSetStart.append(bestsetWeight)
#    bestSetMonte.append(bestSetStart)
#with open('bestSettings_{}.py'.format(c,'w')) as f:
#    f.write('[monte[start[weight[mag]]]]\nbestSettings = '+str(bestSetMonte))
#         with open('/home/mj1e16/keplerPhotometry/starting_{}_ccd_{}_hillClimbRes.py'.format(starting,c),'a') as f:
#             for y in range(len(bestSettings)):
#                 for x in range(len(bestsetWeight))
#                     f.write('\nmonte-{}-mag-{} = '.format(x,mags[y])+str(bestsetWeight[x][y]))
#                 f.write('\n')


# In[ ]:




