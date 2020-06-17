# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 11:00:02 2020

@author: bradford.bates
"""

# Paths.
HEADWATER_NODES = r'X:\datasets\nwm\v2_1\dev\RouteLink_2_1_2019_05_09.gdb\Headwater_Nodes_20190509'  # Temporary

# Projections.
PREP_PROJECTION = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m no_defs'  # from preprocess_gis.sh

# -- Data URLs-- #
NHD_URL_PARENT = r'ftp://rockyftp.cr.usgs.gov/vdelivery/Datasets/Staged/Hydrography/NHDPlus/HU4/HighResolution/GDB/'
NWM_HYDROFABRIC_URL = r'http://www.nohrsc.noaa.gov/pub/staff/keicher/NWM_live/web/data_tools/NWM_channel_hydrofabric.tar.gz'  # Temporary
WBD_NATIONAL_URL = r'https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/WBD/National/GDB/WBD_National_GDB.zip'
WBD_HU2_URL_PARENT = r'http://prd-tnm.s3-website-us-west-2.amazonaws.com/?prefix=StagedProducts/Hydrography/WBD/HU2/GDB'

# -- Prefixes and Suffixes -- #
NHD_URL_PREFIX = 'NHDPLUS_H_'
NHD_RASTER_URL_SUFFIX = '_HU4_RASTER.7z'
NHD_VECTOR_URL_SUFFIX = '_HU4_GDB.zip'
NHD_RASTER_EXTRACTION_PREFIX = 'HRNHDPlusRasters'
NHD_RASTER_EXTRACTION_SUFFIX = 'elev_cm.tif'

NHD_VECTOR_EXTRACTION_PREFIX = 'NHDPLUS_H_'
NHD_VECTOR_EXTRACTION_SUFFIX = '_HU4_GDB.zip'

# -- Field Names -- #
FOSS_ID = 'fossid'

# -- Other -- #
CONUS_STATE_LIST = ["AL", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
                    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]