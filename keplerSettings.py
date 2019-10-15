import numpy as np
import sys

sextractorDirectory = '/home/mj1e16/sextractor/sextractor-master/config/' # directory containing sextractor 
simulatedImageDirectory = '/home/mj1e16/Simages/' # directory where the images with added objects will be stored
imageName = '/data/mj1e16/kepler/cal/kplr2009114174833_ffi-cal.fits' # name of image to be investigated
differenceImageName = '/home/mj1e16/Simages/diff_63_1.fits' # name of difference image made from the target

irafOutputDir = '/home/mj1e16/iraf/outputs/' # directory for intermediate iraf outputs, very important to only store these data here as the directory gets wiped each run
irafImageDir = '/home/mj1e16/Simages/irafImages/' # directory for intermediate iraf images, very important to only store these data here as the directory gets wiped each run
simImageDir = '/home/mj1e16/Simages/' # Directory for images with simulated objects to be stored
irafDir = '/home/mj1e16/iraf/' # directory with iraf installation
starlistDir = '/home/mj1e16/starlists/' # directory to store starlists
workflowDir = '/home/mj1e16/keplerPhotometry/'

sparkHome = '/home/mj1e16/miniconda2/lib/python2.7/site-packages/pyspark' # directory for the spark installation, leave blank to trust in findspark

sqlalchemyURL = 'mysql://mj1e16:[sqlT1G3R]@localhost/Kepler'
mysqlSQLConnector = '/home/mj1e16/miniconda2/lib/python2.7/site-packages/pyspark/mysql-connector-java_8.0.16-1ubuntu16.04_all/usr/share/java/mysql-connector-java-8.0.16.jar' # location of mysql connector jar file
sparkConfig = [('spark.executor.cores', '6'),('spark.cores.max', '6'),('spark.driver.memory','1g'),('spark.executor.memory', '500m'),("spark.sql.execution.arrow.enabled", "true")] # spark settings, adjust for your avaliable resources 

magRange = [-7,-6,-5,-4,-3,-2,-1]
magRangeSQLnaming = [abs(x) for x in magRange] # mag range, without minus signs as sql tables can not include them

databaseTableName = 'hillClimbFinal' # start of the names for tables produced by the code, each will be proceded by _{}_{}_{}.format(ccd,1,mag) followed by the indexes of the values used in the sextractorValueList
databaseLoc = "jdbc:mysql://localhost/Kepler" # url of the database for mysqlcontext
databaseUsername = "mj1e16"
databasePassword = "[sqlT1G3R]"
databaseName = 'Kepler'

astroImageXlength = 1030. # horizontal image length in pixels 
astroImageYlength = 1100. # vertical image length in pixels 
border = 15 # ususally zero, only required if the images have outer regions where you do not want to simulate objects.
astroImageXlength += -border
astroImageYlength += -border
imageZeroPoint = 25. # zero point in magnitudes of the image
xyofSearchBox = 0.5 # used to cross match the object with a square box with sides of this length in pixels 

Weight = 0.5 # relative importance of completeness vs accuracy - Quality = weight*completeness + (1-weight)*accuracy
nsegs = 4 # Number of segments for which PSFs are calculated in both x and y - too many segments and there may not be enough stars for PSF fitting
totalObjects = 1000 # total number of objects to be simulated accross each image
#weightRange = [1,2,3,4,5,6,7,8,9] # test for hill climbing, will be these numbers / 10, important to keep as integers to avoid decimal points in sql column names

sextractorAttributeList = ['DETECT_THRESH','DETECT_MINAREA','FILTER_NAME'] # name of attributes to be altered
sextractorValueList = [np.linspace(1,10,10),np.linspace(1,9,9),['default.conv','gauss_1.5_3x3.conv','gauss_2.0_3x3.conv','gauss_2.0_5x5.conv',
                                                    'gauss_2.5_5x5.conv','gauss_3.0_5x5.conv','gauss_3.0_7x7.conv',
                                                    'gauss_4.0_7x7.conv','gauss_5.0_9x9.conv','mexhat_1.5_5x5.conv',
                                                    'mexhat_2.0_7x7.conv','mexhat_2.5_7x7.conv','mexhat_3.0_9x9.conv',
                                                    'mexhat_4.0_9x9.conv','mexhat_5.0_11x11.conv','tophat_1.5_3x3.conv',
                                                    'tophat_2.0_3x3.conv','tophat_2.5_3x3.conv','tophat_3.0_3x3.conv',
                                                    'tophat_4.0_5x5.conv','tophat_5.0_5x5.conv']]# value ranges of attributes in corresponding order

#sextractorValueList = [np.linspace(1,10,2),np.linspace(1,9,2),['default.conv']]# value ranges of attributes in corresponding order
#ccdExtensions = [79] # ccd extension of the target image 

ccdExtensions = [int((sys.argv[1]))]


