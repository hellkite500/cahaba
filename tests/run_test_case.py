#!/usr/bin/env python3

import pandas as pd
import rasterio
import json
from pprint import pprint
from collections import Counter

from utils.shared_functions import get_contingency_table_from_binary_rasters, compute_stats_from_contingency_table, profile_test_case_archive

#from inundation import inundate



def compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster=None, stats_csv=None, stats_json=None):
    
    # Get cell size of benchmark raster.
    raster = rasterio.open(benchmark_raster_path)
    t = raster.transform
    cell_area = t[0]
        
    # Get contingency table from two rasters.
    contingency_table_dictionary = get_contingency_table_from_binary_rasters(benchmark_raster_path, predicted_raster_path, agreement_raster)
    true_negatives = contingency_table_dictionary['true_negatives']
    false_negatives = contingency_table_dictionary['false_negatives']
    false_positives = contingency_table_dictionary['false_positives']
    true_positives = contingency_table_dictionary['true_positives']
    
    # Produce statistics from continency table and assign to dictionary. cell_area argument optional (defaults to None). 
    stats_dictionary = compute_stats_from_contingency_table(true_negatives, false_negatives, false_positives, true_positives, cell_area)

    # Write the stats_dictionary to the stats_csv.
    if stats_csv != None:
        
        df = pd.DataFrame.from_dict(stats_dictionary, orient="index", columns=['value'])
        df.to_csv(stats_csv)
        
    if stats_json != None:
        with open(stats_json, "w") as outfile:  
            json.dump(stats_dictionary, outfile) 
    
    return stats_dictionary
    

def check_for_regression(stats_json_to_test, previous_version, previous_version_stats_json_path, regression_test_csv=None):
    
    difference_dict = {}
    
    # Compare stats_csv to previous_version_stats_file
    stats_dict_to_test = json.load(open(stats_json_to_test))
    previous_version_stats_dict = json.load(open(previous_version_stats_json_path))
    
    for stat, value in stats_dict_to_test.items():
        previous_version_value = previous_version_stats_dict[stat]
        stat_value_diff = value - previous_version_value
        difference_dict.update({stat + '_diff': stat_value_diff})
    
    return difference_dict


if __name__ == '__main__':
        
    # These will be passed from inundate.
#    rem = ''
#    catchments = ''
#    forecast = ''
#    rating_curve = ''
#    cross_walk = ''
    inundation_raster = r"C:\Users\bradford.bates\Desktop\fim_share\foss_fim_new2\test_cases\ble\ble_huc_12090301\ble_huc_12090301_100yr\ble_huc_12090301_inundation_extent_100yr.tif"
#    inundation_polygon = ''
#    depths = ''
#    
#    # Run inundate.
#    inundate(rem, catchments, forecast, rating_curve, cross_walk, inundation_raster, inundation_polygon, depths)
#    
    
    
    
    predicted_raster_path = inundation_raster
    benchmark_raster_path = r"C:\Users\bradford.bates\Desktop\fim_share\foss_fim_new2\test_cases\ble\ble_huc_12090301\ble_huc_12090301_500yr\ble_huc_12090301_inundation_extent_500yr.tif"
    agreement_raster = r'C:\Users\bradford.bates\Desktop\fim_share\foss_fim_new2\test_cases\ble\ble_huc_12090301\testing2\agreement3.tif'
    stats_json = r'C:\Users\bradford.bates\Desktop\fim_share\foss_fim_new2\test_cases\ble\ble_huc_12090301\testing2\stats3.json'
    stats_csv = r'C:\Users\bradford.bates\Desktop\fim_share\foss_fim_new2\test_cases\ble\ble_huc_12090301\testing2\stats3.csv'
#    stats_dictionary = compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster, stats_csv=stats_csv, stats_json=stats_json)
    
    # Compare to previous stats files that are available.    
    archive_to_check = r'C:\Users\bradford.bates\Desktop\fim_share\foss_fim_new2\test_cases\archive\12090301\ble_archive'
    archive_dictionary = profile_test_case_archive(archive_to_check)

    regression_dict = {}
    for previous_version, paths in archive_dictionary.items():
        print("Comparing results to " + previous_version)
        previous_version_stats_json_path = paths['stats_json']
        difference_dict = check_for_regression(stats_json, previous_version, previous_version_stats_json_path)
        
        # Append results
        regression_dict.update({previous_version: difference_dict})
        
    # Write test results.
    pprint(regression_dict)
    
    















