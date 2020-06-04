# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 10:58:34 2020

@author: bradford.bates
"""

import os
import csv
import sys
from multiprocessing import Pool

NUM_OF_WORKERS = 2
from utils.shared_variables import (NHD_URL_PARENT,
                                    NHD_URL_PREFIX,
                                    NHD_RASTER_URL_SUFFIX,
                                    NHD_VECTOR_URL_SUFFIX,
                                    NHD_RASTER_EXTRACTION_PREFIX,
                                    NHD_RASTER_EXTRACTION_SUFFIX,
                                    NHD_VECTOR_EXTRACTION_PREFIX,
                                    NHD_VECTOR_EXTRACTION_SUFFIX)

from utils.shared_functions import pull_file



def manage_preprocessing(hucs_of_interest_file_path, path_to_saved_data_parent_dir):
    """
    This functions manages the downloading and preprocessing of gridded and vector data for FIM production.
    
    Args:
        hucs_of_interest_file_path (str): Path to a user-supplied config file of hydrologic unit codes to be pulled and post-processed.
        path_to_saved_data_parent_dir (str): Path to directory where raw data and post-processed data will be saved.
    Returns: TBD
    """
        
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
        nhd_raster_extraction_parent = os.path.join(nhd_raster_dir, NHD_RASTER_EXTRACTION_PREFIX + huc)
        if not os.path.exists(nhd_raster_extraction_parent):
            os.mkdir(nhd_raster_extraction_parent)
        nhd_raster_extraction_path = os.path.join(nhd_raster_extraction_parent, NHD_RASTER_EXTRACTION_SUFFIX)
        
        # Construct URL and extraction path for NHDPlus vector.
        nhd_vector_download_url = os.path.join(NHD_URL_PARENT, NHD_URL_PREFIX + huc + NHD_VECTOR_URL_SUFFIX)
        nhd_vector_extraction_path = os.path.join(vector_data_dir, NHD_VECTOR_EXTRACTION_PREFIX + huc + NHD_VECTOR_EXTRACTION_SUFFIX)
    
        pool = Pool(NUM_OF_WORKERS)
        pool.map(pull_file, [[nhd_raster_download_url, nhd_raster_extraction_path], [nhd_vector_download_url, nhd_vector_extraction_path]])
        
        


if __name__ == '__main__':
    
    # Get input arguments from command line.
    hucs_of_interest_file_path = sys.argv[1]
    path_to_saved_data_parent_dir = sys.argv[2]  # The parent directory for all saved data.
    
    manage_preprocessing(hucs_of_interest_file_path, path_to_saved_data_parent_dir)


        # Extract geodatabase
        
    
    
    
    
    