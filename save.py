from astropy.io import ascii
from sqlalchemy import create_engine
import sqlite3
import mysql.connector
import time

def findMatchers(tableName,diffSize=1):

    engine = create_engine('mysql://mj1e16:[sqlT1G3R]@localhost/Kepler')
    conn = mysql.connector.Connect(host='localhost',user='mj1e16',password='[sqlT1G3R]',database='Kepler')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE starlist SET starlist.X_POS_MAX = starlist.X_POS + '+str(diffSize))
    cursor.execute('UPDATE starlist SET starlist.Y_POS_MAX = starlist.Y_POS + '+str(diffSize))
    cursor.execute('UPDATE starlist SET starlist.X_POS_MIN = starlist.X_POS - '+str(diffSize))
    cursor.execute('UPDATE starlist SET starlist.Y_POS_MIN = starlist.Y_POS - '+str(diffSize))

    cursor.execute("SELECT * FROM {} INNER JOIN starlist ON {}.X_IMAGE BETWEEN starlist.X_POS_MIN AND starlist.X_POS_MAX AND {}.Y_IMAGE BETWEEN starlist.Y_POS_MIN AND starlist.Y_POS_MAX;".format(tableName,tableName,tableName))
    dataframe = DataFrame(cursor.fetchall())
    
    newTableName = 'result_'+tableName
    #print(len(dataframe))
    df = dataframe.drop_duplicates(subset=[3,4,5,6,7,8],keep='first')
    #df.to_sql(newTableName,con=engine)
    print(len(df))
    

