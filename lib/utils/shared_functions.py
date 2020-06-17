# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 12:37:15 2020

@author: bradford.bates
"""

import os


def pull_file(url, full_pulled_filepath):
    """
    This helper function pulls a file and saves it to a specified path.
    
    Args:
        url (str): The full URL to the file to download.
        full_pulled_filepath (str): The full system path where the downloaded file will be saved.
    """
    import urllib.request
    
    print("Pulling " + url)
    urllib.request.urlretrieve(url, full_pulled_filepath)

        
def run_system_command(args):
    """
    This helper function takes a system command and runs it. This function is designed for use
    in multiprocessing.
    
    Args:
        args (list): A single-item list, the first and only item being a system command string.
    """
    
    # Parse system command.
    command = args[0]
    
    # Run system command.
    os.system(command)
    
    
def subset_wbd_gpkg(args):
    
    import geopandas as gp
    from utils.shared_variables import CONUS_STATE_LIST
    
    # Parse geopackage path.
    wbd_gpkg = args[0]
    
    print("Subsetting " + wbd_gpkg + "...")
    
    # Read geopackage into dataframe.
    wbd = gp.read_file(wbd_gpkg)
    gdf=gp.GeoDataFrame(wbd)
    
    # Delete OCONUS polygons from the watershed boundary dataset.
    for index, row in gdf.iterrows():
        state = row["STATES"]
        wbd_state_list = state.split(",")  # Some polygons have multiple states, separated by a comma.
        keep_flag = False  # Default to Fault, i.e. to delete the polygon.
        for wbd_state in wbd_state_list:
            if wbd_state in CONUS_STATE_LIST:  # Check each polygon to make sure it's state abbrev name is allowed.
                keep_flag = True
        if not keep_flag:
            gdf.drop(index, inplace=True)  # Delete from dataframe.
        
        # Overwrite geopackage.
        gdf.to_file(wbd_gpkg, driver='GPKG')


    
    