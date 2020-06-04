# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 11:00:02 2020

@author: bradford.bates
"""


# Projections.
PREP_PROJECTION = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m no_defs'  # from preprocess_gis.sh

# -- Data -- #
# Gridded data download URLs and path extraction strings.
NHD_URL_PARENT = r'ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/Hydrography/NHDPlus/HU4/HighResolution/GDB/'
NHD_URL_PREFIX = 'NHDPLUS_H_'
NHD_RASTER_URL_SUFFIX = '_HU4_RASTER.7z'
NHD_VECTOR_URL_SUFFIX = '_HU4_GDB.zip'
NHD_RASTER_EXTRACTION_PREFIX = 'HRNHDPlusRasters'
NHD_RASTER_EXTRACTION_SUFFIX = 'elev_cm.tif'

NHD_VECTOR_EXTRACTION_PREFIX = 'NHDPLUS_H_'
NHD_VECTOR_EXTRACTION_SUFFIX = '_HU4_GDB.zip'
