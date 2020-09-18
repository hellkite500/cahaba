#!/usr/bin/env python3
#
# USAGE:
# ./reachID_grid_to_vector_points.py <flows_grid_IDs raster file> <flows_points vector file> <reachID or featureID>
#
import sys
import numpy as np
from tqdm import tqdm
import geopandas as gpd
from shapely.geometry import Point
import rasterio

import cProfile

path = sys.argv[1]
outputFileName = sys.argv[2]
writeOption = sys.argv[3]

with rasterio.open(path, 'r') as ds:
    data = ds.read(1)
    crs = ds.crs
    (upper_left_x, x_size, 
        x_rotation, upper_left_y, 
        y_rotation, y_size) = ds.transform.to_gdal()

if writeOption == 'reachID':
    a = data.astype(np.float)

indices = np.nonzero(data >= 1)

indx = [None] * len(indices[0])
points = [None]*len(indices[0])

# Iterate over the Numpy points..
i = 1
for y_index,x_index in tqdm(zip(*indices),total=len(indices[0])):
    x = x_index * x_size + upper_left_x + (x_size / 2) #add half the cell size
    y = y_index * y_size + upper_left_y + (y_size / 2) #to centre the point

    points[i-1] = Point(x,y)

    if writeOption == 'reachID':
        reachID = a[y_index,x_index]
        indx[i-1] = reachID
    elif (writeOption == 'featureID') | ( writeOption == 'pixelID'):
        indx[i-1] = i

    i += 1

pointGDF = gpd.GeoDataFrame(
    {'id' : indx, 'geometry' : points},
    crs=crs,
    geometry='geometry'
)
pointGDF.to_file(outputFileName, driver='GPKG', index=False)

print("Complete")
