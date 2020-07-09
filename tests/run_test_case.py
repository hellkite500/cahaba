#!/usr/bin/env python3

import os
import pandas as pd
import rasterio
import json
import csv
import argparse

from utils.shared_functions import get_contingency_table_from_binary_rasters, compute_stats_from_contingency_table

TEST_CASES_DIR = r'/data/test_cases/'  # Will update.
INPUTS_DIR = r'/data/inputs'

from inundation import inundate


def profile_test_case_archive(archive_to_check, return_interval):
    """
    This function searches multiple directories and locates previously produced performance statistics.
    
    Args:
        archive_to_check (str): The directory path to search.
        return_interval (str): Because a benchmark dataset may have multiple return intervals, this argument defines
                               which return interval is to be used when searching for previous statistics.
    Returns:
        archive_dictionary (dict): A dictionary of available statistics for previous versions of the domain and return interval.
                                  {version: {agreement_raster: agreement_raster_path, stats_csv: stats_csv_path, stats_json: stats_json_path}}
                                  *Will only add the paths to files that exist.
    
    """
    
    archive_dictionary = {}
    
    # List through previous version and check for available stats and maps. If available, add to dictionary.
    available_versions_list = os.listdir(archive_to_check)
    for version in available_versions_list:
        version_return_interval_dir = os.path.join(archive_to_check, version, return_interval)
        # Initialize dictionary for version and set paths to None by default.
        archive_dictionary.update({version: {'agreement_raster': None,
                                             'stats_csv': None,
                                             'stats_json': None}})
        # Find stats files and raster files and add to dictionary.
        agreement_raster = os.path.join(version_return_interval_dir, 'agreement.tif')
        stats_csv = os.path.join(version_return_interval_dir, 'stats.csv')
        stats_json = os.path.join(version_return_interval_dir, 'stats.json')
        
        if os.path.exists(agreement_raster):
            archive_dictionary[version]['agreement_raster'] = agreement_raster
        if os.path.exists(stats_csv):
            archive_dictionary[version]['stats_csv'] = stats_csv
        if os.path.exists(stats_json):
            archive_dictionary[version]['stats_json'] = stats_json
        
    return archive_dictionary


def compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster=None, stats_csv=None, stats_json=None):
    """
    This function contains FIM-specific logic to prepare raster datasets for use in the generic get_contingency_table_from_binary_rasters() function.
    This function also calls the generic compute_stats_from_contingency_table() function and writes the results to CSV and/or JSON, depending on user input.
    
    Args:
        predicted_raster_path (str): The path to the predicted, or modeled, FIM extent raster.
        benchmark_raster_path (str): The path to the benchmark, or truth, FIM extent raster.
        agreement_raster (str): Optional. An agreement raster will be written to this path. 0: True Negatives, 1: False Negative, 2: False Positive, 3: True Positive.
        stats_csv (str): Optional. Performance statistics will be written to this path. CSV allows for readability and other tabular processes.
        stats_json (str): Optional. Performance statistics will be written to this path. JSON allows for quick ingestion into Python dictionary in other processes.
        
    Returns:
        stats_dictionary (dict): A dictionary of statistics produced by compute_stats_from_contingency_table(). Statistic names are keys and statistic values are the values.
    """
    
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


def run_alpha_test(fim_run_dir, branch_name, test_id, return_interval, compare_to_previous):
    
    # Create paths to fim_run outputs for use in inundate().
    rem = os.path.join(fim_run_dir, 'rem_clipped_zeroed_masked.tif')
    catchments = os.path.join(fim_run_dir, 'gw_catchments_reaches_clipped_addedAttributes.tif')
    rating_curve = os.path.join(fim_run_dir, 'src.json')  # Will be replaced by hydrotable
    cross_walk = os.path.join(fim_run_dir, 'crosswalk_table.csv')  # Will be replaced by hydrotable
    current_huc = test_id.split('_')[0]
    hucs, hucs_layerName = os.path.join(INPUTS_DIR, 'wbd', 'WBD_National.gpkg'), 'WBDHU8'
    
    # Construct paths to development test results if not existent.
    branch_test_case_dir = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'development_versions', branch_name, return_interval)
    if not os.path.exists(branch_test_case_dir):
        os.makedirs(branch_test_case_dir)
    
    inundation_raster = os.path.join(branch_test_case_dir, 'inundation_extent.tif')
        
    # Construct path to validation raster and forecast file.
    benchmark_category = test_id.split('_')[1]
    benchmark_raster_path = os.path.join(TEST_CASES_DIR, test_id, 'validation_data', return_interval, benchmark_category + '_huc_' + current_huc + '_inundation_extent_' + return_interval + '.tif')
    forecast = os.path.join(TEST_CASES_DIR, test_id, 'validation_data', return_interval, benchmark_category + '_huc_' + current_huc + '_flows_' + return_interval + '.csv')

    # Run inundate.
    print("Running inundation...")
    inundate(rem,catchments,forecast,rating_curve,cross_walk,hucs=hucs,
             hucs_layerName=hucs_layerName,num_workers=1,inundation_raster=inundation_raster,inundation_polygon=None,
             depths=None,out_raster_profile=None,out_vector_profile=None,aggregate=False,current_huc=current_huc)

    predicted_raster_path = os.path.join(os.path.split(inundation_raster)[0], os.path.split(inundation_raster)[1].replace('.tif', '_' + current_huc + '.tif'))  # The inundate adds the huc to the name so I account for that here.

    # Define outputs for agreement_raster, stats_json, and stats_csv.
    print("Comparing predicted inundation to benchmark inundation...")
    agreement_raster, stats_json, stats_csv = os.path.join(branch_test_case_dir, 'agreement.tif'), os.path.join(branch_test_case_dir, 'stats.json'), os.path.join(branch_test_case_dir, 'stats.csv')
    compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster, stats_csv=stats_csv, stats_json=stats_json)
    
    if compare_to_previous:
        # Compare to previous stats files that are available.    
        archive_to_check = os.path.join(TEST_CASES_DIR, current_huc, benchmark_category, 'performance_archive', 'previous_versions')
        archive_dictionary = profile_test_case_archive(archive_to_check, return_interval)
        regression_dict = {}
        for previous_version, paths in archive_dictionary.items():
            print("Comparing results to " + previous_version)
            previous_version_stats_json_path = paths['stats_json']
            difference_dict = check_for_regression(stats_json, previous_version, previous_version_stats_json_path)
            regression_dict.update({previous_version: difference_dict})
            
        # Parse values from dictionary for writing. Not the most Pythonic, but works fast.
        version_list = list(regression_dict.keys())
        stat_names_list = list(regression_dict[version_list[0]].keys())
        lines = []
        for stat in stat_names_list:
            stat_line = []
            for version in version_list:
                stat_line.append(regression_dict[version][stat])
            stat_line.insert(0, stat)
            lines.append(stat_line)
        version_list.insert(0, " ")
        
        # Write test results.
        regression_report_csv = os.path.join(branch_test_case_dir, 'regression_report.csv')
        with open(regression_report_csv, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(version_list)
            csv_writer.writerows(lines)
          
    print(" ")
    print("Completed. Stats outputs for " + test_id + " are in " + branch_test_case_dir)
    print(" ")
    

if __name__ == '__main__':
    
    # Parse arguments.
    parser = argparse.ArgumentParser(description='Inundation mapping and regression analysis for FOSS FIM. Regression analysis results are stored in the test directory.')
    parser.add_argument('-r','--fim-run-dir',help='Path to directory containing outputs of fim_run.sh',required=True)
    parser.add_argument('-b', '--branch-name',help='The name of the working branch in which features are being tested',required=True,default="")
    parser.add_argument('-t','--test-id',help='The test_id to use. Format as: HUC_BENCHMARKTYPE, e.g. 12345678_ble.',required=True,default="")
    parser.add_argument('-y', '--return-interval',help='The return interval to check. Options include: 100yr, 500yr',required=True,default="BLE")
    parser.add_argument('-c', '--compare-to-previous', help='Compare to previous versions of HAND.', required=False,action='store_true')
    
    # Extract to dictionary and assign to variables.
    args = vars(parser.parse_args())
    
    # TEMPORARY CODE
    if args['test_id'] != '12090301_ble' or args['compare_to_previous'] == True:
        import sys
        print("Only the 12090301_ble test case is supported at this time. Additional benchmark data are being processed and will be added soon. Compare previous versions (-c) will be available after backfilling has been done.")
        sys.exit()
    else:  
        run_alpha_test(**args)

    