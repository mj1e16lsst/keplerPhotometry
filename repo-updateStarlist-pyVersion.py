
# coding: utf-8

# In[11]:


import keplerSettings

from astropy.io import ascii
import mysql.connector
from pandas import DataFrame
import mysql.connector
from sqlalchemy import create_engine


# In[12]:


engine = create_engine(keplerSettings.sqlalchemyURL)
conn = mysql.connector.Connect(host='localhost',user=keplerSettings.databaseUsername,password=keplerSettings.databasePassword,database=keplerSettings.databaseName)
cursor = conn.cursor()


# In[13]:


for mag in keplerSettings.magRange:
    cursor.execute('DROP TABLE IF EXISTS starlist_{}'.format(abs(mag)))
    data = ascii.read(keplerSettings.workflowDir+'starlistFull_{}.dat'.format(mag)) 
    df = data.to_pandas()
    #print(df)
    diffSize = .5

    df['X_POS_MAX'] = df['X_POS'] + diffSize
    df['Y_POS_MAX'] = df['Y_POS'] + diffSize
    df['X_POS_MIN'] = df['X_POS'] - diffSize
    df['Y_POS_MIN'] = df['Y_POS'] - diffSize
    df.to_sql('starlist_{}'.format(abs(mag)),con=engine)


# In[ ]:




