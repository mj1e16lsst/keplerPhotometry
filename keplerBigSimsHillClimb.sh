#!/bin/bash

cp /home/mj1e16/keplerPhotometry/keplerSettings.py /home/mj1e16/iraf/keplerSettings.py

for VARIABLE in 63
do 
	 
	source activate iraf270
	cd /home/mj1e16/iraf
	./ds9 &
	python repo-irafMkObjects-pyupgrade.py $VARIABLE

	source deactivate iraf270
	source activate astroconda
	cd /home/mj1e16/keplerPhotometry
	python repo-updateStarlist-pyVersion.py $VARIABLE
	python repo-workFlow-Single-update-Hillclimb-topy.py $VARIABLE
done




