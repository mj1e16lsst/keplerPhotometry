
# coding: utf-8

# In[1]:


from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt
import os


# In[2]:


imageDirectory = '/data/mj1e16/kepler/cal/'
dirlist = os.listdir(imageDirectory)
dirlist = [x for x in dirlist if x[0] != '.']
print(dirlist)


# In[3]:


hdu_list = fits.open(imageDirectory+'kplr2012121122500_ffi-cal.fits')
imagelist = [imageDirectory+x for x in dirlist]
image_concat = [[]]*(len(hdu_list))


for image in imagelist:
    hdu_list = fits.open(image)
    #print(len(hdu_list))
    for ccd in range(1,len(hdu_list)):
        image_data = hdu_list[ccd].data
        
        image_concat[ccd].append(image_data)


# In[5]:


#final_image = np.zeros(shape=image_concat[0].shape)
## add stacked images and median
for ccd in range(1): #len(image_concat)):
    final_image = np.sum(image_concat,axis=0)
    median_image = np.median(final_image,axis=0)
    plt.imshow(median_image,cmap='grey',norm=LogNorm())
    plt.show()
    
    

