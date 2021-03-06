#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Plot the YOLOv3 detections on the dynamic spectra


"""
import os
import pdb
import time

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from radiospectra import spectrogram
from datetime import datetime
from spectro_prep import rfi_removal, backsub 


#-------------------------------------#
#
#      		 Functions
#
def yolo_results_parser(txt):
    file = open(txt, 'r')
    yolo_results = np.array(list(file))

    yolo_dict = {}
    img_indices = []
    [img_indices.append(index) for index, row in enumerate(yolo_results) if row[0]=='E']

    for i in np.arange(len(img_indices)-1):
        bursts = []
        result = yolo_results[img_indices[i]:img_indices[i+1]]
        img_name = result[0].split('/')[2].split('.')[0]
        print(img_name)
        txt_coords = result[1::]
        for txt_coord in txt_coords:
            coords = np.array(txt_coord.split('(')[1].split(')')[0].split(' '))
            coords = coords[coords!='']
            bursts.append(coords[[1,3,5,7]].astype(np.float).tolist())
        yolo_dict[img_name]=bursts

    return yolo_dict    


def get_box_coords(coords, nx, ny):

	# Awkardly, the x0, y0 points for the patches.rectangle procedure is a little 
	# different to how the coords are defined by yolo. This converts from one to the other.

	x0, y0 = int(coords[0]*nx), int(coords[1]*ny)

	width, height = coords[2]*nx, coords[3]*ny
	y1 = ny - (y0 + height)  # Note that pacthes.Rectangle measure the y-coord from the bottom.
	x1 = int(x0 + width)

	spill=x1-(nx-2) if x1>=(nx-5) else 0
	width = width-spill
	
	if y1<0: height=height+y1
	boxx0 = np.clip(x0, 0, nx)
	boxy0 = np.clip(y1, 0, ny)

	return x0, y0, x1, y1, boxx0, boxy0, width, height


#-------------------------------------#
#
#      		 Main procedure
#
if __name__ == '__main__':

	IE613_file = '20170910_070804_bst_00X.npy'
	event_date = IE613_file.split('_')[0]
	file_path = '../Inception/classify_'+event_date+'/'
	output_path = 'data/IE613_detections/'
	img_sz = 512
	timestep = 30  # Seconds 

	#-------------------------------------#
	#
	#      Read in IE613 spectrogram
	#
	result = np.load(file_path+IE613_file)
	spectro = result[0]['data']                     # Spectrogram of entire day
	freqs = np.array(result[0]['freq'])             # In MHz
	timesut_total = np.array(result[0]['time'])     # In UTC

	# Sort frequencies
	spectro = spectro[::-1, ::]                     # Reverse spectrogram. For plotting high -> low frequency
	freqs = freqs[::-1]                             # For plotting high -> low frequency
	#spectro = backsub(spectro)
	indices = np.where( (freqs>=20.0) \
					& (freqs<=100.0) )              # Taking only the LBA frequencies
	freqs = freqs[indices[0]]
	spectro = spectro[indices[0], ::]
	nfreqs = len(freqs)
	nspecfreqs = nfreqs*2			# The spectro plotter doubles the amount of y points.

	# Sort time
	block_sz = 10.0 # minutes
	time_start = timesut_total[0] #datetime(2017, 9, 2, 10, 46, 0).timestamp() 
	time0global = time_start 
	time1global = time_start  + 60.0*block_sz      
	deltglobal = timesut_total[-1] - timesut_total[0]
	trange = np.arange(0, deltglobal, timestep)

	yolo_allburst_coords = yolo_results_parser('IE613_detections_600_0010_20190110.txt')

	for img_index,tstep in enumerate(trange):
		#-------------------------------------#
		#     Select block of time. 
		#     Shifts by tstep every iteration of the loop.
		#
		time_start = time0global + tstep
		time_stop = time1global + tstep
		time_index = np.where( (timesut_total >= time_start) 
		                        & (timesut_total <= time_stop))
		times_ut = timesut_total[time_index[0]]
		data = spectro[::, time_index[0]] #mode 3 reading
		data = backsub(data)
		data[121:123, ::] = np.median(data)
		delta_t = times_ut - times_ut[0]
		ntimes = len(delta_t)
		times_dt = [datetime.fromtimestamp(t) for t in times_ut]
		time0_str = times_dt[0].strftime('%Y%m%d_%H%M%S')
		img_key = 'image_'+time0_str

		fig = plt.figure(2, figsize=(10,7))

		#----------------------------------------#
		#
		#		Plot original spectrogram
		#
		ax0 = fig.add_axes([0.1, 0.54, 0.8, 0.38])

		spec = spectrogram.Spectrogram(data, delta_t, freqs, times_dt[0], times_dt[-1])
		scl1 = 0.995 #data.mean() #- data.std()
		scl2 = 1.025 #data.mean() + data.std()*4.0
		spec.t_label=' '
		spec.plot(vmin=scl1, 
		           vmax=scl2, 
		           cmap=plt.get_cmap('bone'), colorbar=False)
		plt.xticks([])
		spec.t_label=' '
		plt.text(190, 365, 'I-LOFAR YOLOv3 type III detections, %s' %(times_dt[0].strftime('%Y-%m-%d')))

		#------------------------------------------#
		#
		#	Plot the spectrogram with detections 
		#   on bottom of figure.
		#
		#
		ax1 = fig.add_axes([0.1, 0.135, 0.8, 0.385])
		spec.t_label='Time (UT)'
		spec.plot(vmin=scl1, 
		          vmax=scl2, 
		          cmap=plt.get_cmap('bone'), axnum=1, colorbar=False)

		yolo_burst_coords = yolo_allburst_coords[img_key]

		for burstcoords in yolo_burst_coords:
			burstcoords = np.clip(np.array(burstcoords), 4, 508)/img_sz # Clip because YOLO sometimes gives negative coords

			x0, y0, x1, y1, boxx0, boxy0, width, height = get_box_coords(burstcoords, ntimes, nspecfreqs)

			rect = patches.Rectangle( (boxx0, boxy0), width, height, 
					linewidth=0.5, 	
					edgecolor='lawngreen', 
					facecolor='none')  
			ax1.add_patch(rect)

			#----------------------------------#
			#
			#	Plot red points inside boxes
			#	
			y0 = y0//2
			height = int(height/2)
			y1 = y0 + height
			y0index = nfreqs - y1 
			y1index = nfreqs - y0

			data_section = data[y0index:y1index, x0:x1]
			thresh = np.median(data_section)+data_section.std()*0.7
			burst_indices = np.where(data>thresh)

			xpoints, ypoints = burst_indices[1], burst_indices[0]
			box_indices = (xpoints>x0) & \
						  (xpoints<x1) & \
						  (ypoints<y1index) & \
						  (ypoints>y0index)

			xbox, ybox = xpoints[np.where( box_indices )], ypoints[np.where( box_indices )]
			xbox, ybox = np.clip(xbox, 0, ntimes-2), np.clip(ybox, 0, nfreqs-2)

			ax1.scatter(x=xbox, y=ybox*2.0, c='r', s=10, alpha=0.1)	
         	
		out_png = output_path+'/IE613_'+str(format(img_index, '04'))+'_detections.png'
		print("Saving %s" %(out_png))
		fig.savefig(output_path+'/IE613_'+str(format(img_index, '04'))+'_detections.png')
		plt.close(fig)

	    
	#ffmpeg -y -r 20 -i IE613_%04d_detections.png -vb 50M IE613_YOLO_600_0010.mpg
