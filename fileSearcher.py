import os
import subprocess


textLocater = 'beautifulsoup'

dirlist = os.listdir('.')

for i,item in enumerate(dirlist):
	if item[0] != 0 and os.path.isfile(item):
		f = open(item,'r')
		searchString = f.read()
		f.close()
		indicater = searchString.find(textLocater)
		if indicater != -1:
			print(item+ ' - contains '+textLocater)
