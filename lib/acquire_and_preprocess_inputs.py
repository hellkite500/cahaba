# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 10:58:34 2020

@author: bradford.bates
"""

import os
import csv
import sys
from multiprocessing import Pool

NUM_OF_WORKERS = 1
from utils.shared_variables import (NHD_URL_PARENT,
                                    NHD_URL_PREFIX,
                                    NHD_RASTER_URL_SUFFIX,
                                    NHD_VECTOR_URL_SUFFIX,
                                    NHD_RASTER_EXTRACTION_PREFIX,
                                    NHD_RASTER_EXTRACTION_SUFFIX,
                                    NHD_VECTOR_EXTRACTION_PREFIX,
                                    NHD_VECTOR_EXTRACTION_SUFFIX,
                                    PREP_PROJECTION)

from utils.shared_functions import pull_file


def pull_and_prepare_nhd_data(procs_list):
    
    # Parse urls and extraction paths from procs_list.
    nhd_raster_download_url = procs_list[0]
    nhd_raster_extraction_path = procs_list[1]
    nhd_vector_download_url = procs_list[2]
    nhd_vector_extraction_path = procs_list[3]
    
    # Download raster and vector, if not already in user's directory (exist check performed by pull_file()).
    nhd_raster_extraction_parent = os.path.dirname(nhd_raster_extraction_path)
    if not os.path.exists(nhd_raster_extraction_parent):
        os.mkdir(nhd_raster_extraction_parent)
    pull_file(nhd_raster_download_url, nhd_raster_extraction_path)
#    pull_file(nhd_vector_download_url, nhd_vector_extraction_path)
    print("All files pulled.")
    
    # Unzip downloaded vector. Then delete the zipped dir.
    nhd_vector_extraction_parent = os.path.dirname(nhd_vector_extraction_path)
    print(nhd_vector_extraction_parent)
    huc = os.path.split(nhd_vector_extraction_parent)[1]
#    os.system("7za x {nhd_vector_extraction_path} -o{nhd_vector_extraction_parent}".format(nhd_vector_extraction_path=nhd_vector_extraction_path, nhd_vector_extraction_parent=nhd_vector_extraction_parent))
#    os.remove(nhd_vector_extraction_path)  # Delete the zipped GDB.
#    
    # Project and convert vectors to geopackage.
    nhd_gdb = nhd_vector_extraction_path.replace('.zip', '.gdb')
#    os.system("ogr2ogr -overwrite -progress -f GPKG -t_srs "$usgsProjection" $outputDataDir/WBDHU6_1209.gpkg $outputDataDir/NHDPLUS_H_1209_HU4_GDB.gdb WBDHU6"
    os.system('ogr2ogr -overwrite -progress -f GPKG -t_srs "{PREP_PROJECTION}" {burn_line_event_gpkg} {nhd_gdb} NHDPlusBurnLineEvent'.format(PREP_PROJECTION=PREP_PROJECTION, burn_line_event_gpkg=os.path.join(nhd_vector_extraction_parent, 'NHDPlusBurnLineEvent_' + huc + '.gpkg'), nhd_gdb=nhd_gdb))
    
    os.system('ogr2ogr -overwrite -progress -f GPKG -t_srs "{PREP_PROJECTION}" {flow_line_vaa_gpkg} {nhd_gdb} NHDPlusFlowlineVAA'.format(PREP_PROJECTION=PREP_PROJECTION, flow_line_vaa_gpkg=os.path.join(nhd_vector_extraction_parent, 'NHDPlusFlowlineVAA_' + huc + '.gpkg'), nhd_gdb=nhd_gdb))
    
    
#             ogr2ogr -overwrite -progress -f GPKG -t_srs "$usgsProjection" $outputDataDir/NHDPlusFlowlineVAA_1209.gpkg $outputDataDir/NHDPLUS_H_1209_HU4_GDB.gdb NHDPlusFlowlineVAA
    
#        $outputDataDir/NHDPlusBurnLineEvent_1209.gpkg

#ogr2ogr -overwrite -progress -f GPKG -t_srs "$usgsProjection" $outputDataDir/NHDPlusBurnLineEvent_1209.gpkg $outputDataDir/NHDPLUS_H_1209_HU4_GDB.gdb NHDPlusBurnLineEvent
def manage_preprocessing(hucs_of_interest_file_path, path_to_saved_data_parent_dir):
    """
    This functions manages the downloading and preprocessing of gridded and vector data for FIM production.
    
    Args:
        hucs_of_interest_file_path (str): Path to a user-supplied config file of hydrologic unit codes to be pulled and post-processed.
        path_to_saved_data_parent_dir (str): Path to directory where raw data and post-processed data will be saved.
    Returns: TBD
    """
    
    procs_list = []  # Initialize procs_list for multiprocessing.
    
    # Create the parent directory if nonexistent.
    if not os.path.exists(path_to_saved_data_parent_dir):
        os.mkdir(path_to_saved_data_parent_dir)
        
    # Create NHDPlus raster parent directory if nonexistent.
    nhd_raster_dir = os.path.join(path_to_saved_data_parent_dir, 'nhdplus_rasters')
    if not os.path.exists(nhd_raster_dir):
        os.mkdir(nhd_raster_dir)
        
    # Create the vector data parent directory if nonexistent.
    vector_data_dir = os.path.join(path_to_saved_data_parent_dir, 'vector_data')
    if not os.path.exists(vector_data_dir):
        os.mkdir(vector_data_dir)
        
    # Parse HUCs from hucs_of_interest_file_path.
    with open(hucs_of_interest_file_path) as csv_file:  # Does not have to be CSV format.
        huc_list = list(csv.reader(csv_file))
        
    # Construct paths to data to download and append to procs_list for multiprocessed pull, project, and converstion to geopackage.
    for huc in huc_list:
        huc = str(huc[0])
    
        # Construct URL and extraction path for NHDPlus raster.
        nhd_raster_download_url = os.path.join(NHD_URL_PARENT, NHD_URL_PREFIX + huc + NHD_RASTER_URL_SUFFIX)
        nhd_raster_extraction_path = os.path.join(nhd_raster_dir, NHD_RASTER_EXTRACTION_PREFIX + huc, NHD_RASTER_EXTRACTION_SUFFIX)
        
        # Construct URL and extraction path for NHDPlus vector. Organize into huc-level subdirectories.
        nhd_vector_download_url = os.path.join(NHD_URL_PARENT, NHD_URL_PREFIX + huc + NHD_VECTOR_URL_SUFFIX)
        nhd_vector_download_parent = os.path.join(vector_data_dir, huc)
        if not os.path.exists(nhd_vector_download_parent):
            os.mkdir(nhd_vector_download_parent)
        nhd_vector_extraction_path = os.path.join(nhd_vector_download_parent, NHD_VECTOR_EXTRACTION_PREFIX + huc + NHD_VECTOR_EXTRACTION_SUFFIX)

    
        procs_list.append([nhd_raster_download_url, nhd_raster_extraction_path, nhd_vector_download_url, nhd_vector_extraction_path])
        
    # Pull NHD Data.
    pool = Pool(NUM_OF_WORKERS)
    pool.map(pull_and_prepare_nhd_data, procs_list)


if __name__ == '__main__':
    
    # Get input arguments from command line.
    hucs_of_interest_file_path = sys.argv[1]
    path_to_saved_data_parent_dir = sys.argv[2]  # The parent directory for all saved data.
    
    manage_preprocessing(hucs_of_interest_file_path, path_to_saved_data_parent_dir)


        # Extract geodatabase
        
    
    
    
    
    