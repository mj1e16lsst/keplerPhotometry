import subprocess
import keplerSettings
import os

ccds = [44,63,79]
for x in ccds:
	with open('keplerSettings.py','r') as f:
		data = f.read()
	loc1 = data.find('ccdExtensions = [')
	loc2 = data[loc1:].find(']')
	newdata = data[:loc1]+str(x)+data[loc2:]

	subprocess.call(['./iraf.sh'])
	os.chdir(keplerSettings.irafDir)
	subprocess.call(['./ds9','&'])
	subprocess.call(['python','repo-irafMkObjects-pyupgrade.py'])

	os.chdir(keplerSettings.workflowDir)
	subprocess.call(['./astroconda.sh'])
	subprocess.call(['python','repo-updateStarlist-pyVersion.py'])
	subprocess.call(['python','repo-workFlow-Single-update-toPy.py'])
