#!/usr/bin/env python3

import argparse
from pprint import pprint

from utils.shared_functions import get_contingency_table_from_binary_rasters, compute_stats_from_contingency_table

#from inundation import inundate

import rasterio


def compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster=None, stats_csv=None):
    
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
    pprint(stats_dictionary)

    if stats_csv != None:
        pass
        # Write the stats_dictionary to the stats_csv.
    

def check_for_regression(stats_csv_to_test, previous_version, previous_version_stats_csv_path, regression_test_csv):
    print(stats_csv_to_test, previous_version, previous_version_stats_csv_path)

    # Compare stats_csv to previous_version_stats_file


if __name__ == '__main__':
        
    # Parse arguments. Still evolving with reconciliation with inundation.py.
    parser = argparse.ArgumentParser(description='Provide three inundation files to output binary contigency stats. Need to have same spatial extents, projections, and resolutions.')
    parser.add_argument('-p','--predicted', help='Predicted inundation raster filepath', required=True)
    parser.add_argument('-w','--watersheds', help='HUC8 or HUC8s. If multiple, put in quotes and separate with comma', required=True)
    parser.add_argument('-b','--benchmark', help='Benchmark inundation raster filepath', required=True)
    # parser.add_argument('-e','--exclusion-mask',help='Set an exclusion mask to exclude from analysis inside analysis extents',required=False,default=None)
    parser.add_argument('-a','--agreement_raster',help='Filepath where the agreement raster will be saved',required=False,default=None)
    parser.add_argument('-s','--stats',help='Filepath where the contingeny metrics and statistics CSV be saved',required=False,default=None)
    parser.add_argument('-q','--quiet',help='Quiet output',required=False,action='store_false')

    # Extract arguments to dictionary and assign to dictionary.
    args_dictionary = vars(parser.parse_args())
    predicted_raster_path = args_dictionary['predicted']
    benchmark_raster_path = args_dictionary['benchmark']
    huc8s_to_evaluate = args_dictionary['watersheds'].replace(' ', '').split(',')
    agreement_raster = args_dictionary['agreement_raster']
    stats_csv = args_dictionary['stats']
        
#    compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster, stats_csv)
    
    # Compare to previous stats files that are available.
    regression_test_csv = ""
    dict_of_previous_version_stats_csvs = {'version1': 'version1\path',
                                           'version2': 'version2\path',
                                           'version2': 'version2\path'}  # Would be generated from user-provided stats files (directory?).
    
    for previous_version, previous_version_stats_csv_path in dict_of_previous_version_stats_csvs.items():
        check_for_regression(stats_csv, previous_version, previous_version_stats_csv_path, regression_test_csv)
   
    