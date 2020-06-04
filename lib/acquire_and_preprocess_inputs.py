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
                                    NHD_VECTOR_EXTRACTION_SUFFIX)

from utils.shared_functions import pull_file


def preprocess(procs_list):
    
    nhd_raster_download_url = procs_list[0]
    nhd_raster_extraction_path = procs_list[1]
    nhd_vector_download_url = procs_list[2]
    nhd_vector_extraction_path = procs_list[3]

    # Download raster and vector, if not already in user's directory.
    if not os.path.exists(nhd_raster_extraction_path):
        pull_file(nhd_raster_download_url, nhd_raster_extraction_path)
    if not os.path.exists(nhd_vector_extraction_path):
        pull_file(nhd_vector_download_url, nhd_vector_extraction_path)
        
    # Convert vector to geopackage.
        


def manage_preprocessing(hucs_of_interest_file_path, path_to_saved_data_parent_dir):
    """
    This functions manages the downloading and preprocessing of gridded and vector data for FIM production.
    
    Args:
        hucs_of_interest_file_path (str): Path to a user-supplied config file of hydrologic unit codes to be pulled and post-processed.
        path_to_saved_data_parent_dir (str): Path to directory where raw data and post-processed data will be saved.
    Returns: TBD
    """
    
    procs_list = []  # Initialize procs_list for multiprocessing.
    
    # Create the data directory if it doesn't already exist.
    if not os.path.exists(path_to_saved_data_parent_dir):
        os.mkdir(path_to_saved_data_parent_dir)
    
    # Parse HUCs from hucs_of_interest_file_path.
    with open(hucs_of_interest_file_path) as csv_file:  # Does not have to be CSV format.
        huc_list = list(csv.reader(csv_file))
        
    # Construct paths to data to download and extract.
    for huc in huc_list:
        huc = str(huc[0])
    
        # Construct URL and extraction path for NHDPlus raster.
        nhd_raster_download_url = os.path.join(NHD_URL_PARENT, NHD_URL_PREFIX + huc + NHD_RASTER_URL_SUFFIX)
        nhd_raster_extraction_path = os.path.join(path_to_saved_data_parent_dir, NHD_RASTER_EXTRACTION_PREFIX + huc + NHD_RASTER_EXTRACTION_SUFFIX, huc + 'elev_cm.tif')
        
        # Construct URL and extraction path for NHDPlus vector.
        nhd_vector_download_url = os.path.join(NHD_URL_PARENT, NHD_URL_PREFIX + huc + NHD_VECTOR_URL_SUFFIX)
        nhd_vector_extraction_path = os.path.join(path_to_saved_data_parent_dir, NHD_VECTOR_EXTRACTION_PREFIX + huc + NHD_VECTOR_EXTRACTION_SUFFIX)
    
        procs_list.append([nhd_raster_download_url, nhd_raster_extraction_path, nhd_vector_download_url, nhd_vector_extraction_path])
    
    print(procs_list)
    
    pool = Pool(NUM_OF_WORKERS)
    pool.map(preprocess, procs_list)


if __name__ == '__main__':
    
    # Get input arguments from command line.
    hucs_of_interest_file_path = sys.argv[1]
    path_to_saved_data_parent_dir = sys.argv[2]  # The parent directory for all saved data.
    
    manage_preprocessing(hucs_of_interest_file_path, path_to_saved_data_parent_dir)


        # Extract geodatabase
        
    
    
    
    
    