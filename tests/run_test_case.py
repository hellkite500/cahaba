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
SUMMARY_STATS = ['csi', 'pod', 'far', 'MCC', 'bias', 'true_negatives', 'false_negatives', 'true_positives', 'false_positives', ]
GO_UP_STATS = ['csi', 'pod', 'MCC', 'true_negatives', 'true_positives', 'percent_correct']
GO_DOWN_STATS = ['far', 'false_negatives', 'false_positives', 'bias']
OUTPUTS_DIR = os.environ['outputDataDir']

from inundation import inundate


def profile_test_case_archive(archive_to_check, return_interval, stats_mode):
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
        agreement_raster = os.path.join(version_return_interval_dir, stats_mode + '_agreement.tif')
        stats_csv = os.path.join(version_return_interval_dir, stats_mode + '_stats.csv')
        stats_json = os.path.join(version_return_interval_dir, stats_mode + '_stats.json')
        
        if os.path.exists(agreement_raster):
            archive_dictionary[version]['agreement_raster'] = agreement_raster
        if os.path.exists(stats_csv):
            archive_dictionary[version]['stats_csv'] = stats_csv
        if os.path.exists(stats_json):
            archive_dictionary[version]['stats_json'] = stats_json
        
    return archive_dictionary


def compute_contingency_stats_from_rasters(predicted_raster_path, benchmark_raster_path, agreement_raster=None, stats_csv=None, stats_json=None, mask_values=None, stats_modes_list=['total_area'], test_id=''):
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
        
    additional_layers_dict = {}
    # Create path to additional_layer. Could put conditionals here to create path according to some version. Simply use stats_mode for now. Must be raster.
    if len(stats_modes_list) > 1:
        additional_layers_dict = {}
        for stats_mode in stats_modes_list:
            if stats_mode != 'total_area':
                additional_layer_path = os.path.join(TEST_CASES_DIR, test_id, 'additional_layers', stats_mode, stats_mode + '.tif')
                additional_layers_dict.update({stats_mode: additional_layer_path})
    
    # Get contingency table from two rasters.
    contingency_table_dictionary = get_contingency_table_from_binary_rasters(benchmark_raster_path, predicted_raster_path, agreement_raster, mask_values=mask_values, additional_layers_dict=additional_layers_dict)
    
    stats_dictionary = {}
    
    for stats_mode in contingency_table_dictionary:
        print("Running " + stats_mode + "...")
        true_negatives = contingency_table_dictionary[stats_mode]['true_negatives']
        false_negatives = contingency_table_dictionary[stats_mode]['false_negatives']
        false_positives = contingency_table_dictionary[stats_mode]['false_positives']
        true_positives = contingency_table_dictionary[stats_mode]['true_positives']
        
        # Produce statistics from continency table and assign to dictionary. cell_area argument optional (defaults to None). 
        mode_stats_dictionary = compute_stats_from_contingency_table(true_negatives, false_negatives, false_positives, true_positives, cell_area)
        
        # Write the mode_stats_dictionary to the stats_csv.
        if stats_csv != None:
            stats_csv = os.path.join(os.path.split(stats_csv)[0], stats_mode + '_stats.csv')
            df = pd.DataFrame.from_dict(mode_stats_dictionary, orient="index", columns=['value'])
            df.to_csv(stats_csv)
            
        # Write the mode_stats_dictionary to the stats_json.
        if stats_json != None:
            stats_json = os.path.join(os.path.split(stats_csv)[0], stats_mode + '_stats.json')
            with open(stats_json, "w") as outfile:  
                json.dump(mode_stats_dictionary, outfile) 
    
        stats_dictionary.update({stats_mode: mode_stats_dictionary})
        
        
    # Write summary CSV for humans.
        
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
    

def run_alpha_test(fim_run_dir, branch_name, test_id, return_interval, compare_to_previous=False, run_structure_stats=False, archive_results=False, legacy_fim_run_dir=False):
        
    stats_modes_list = ['total_area']
    if run_structure_stats: stats_modes_list.append('structures')
    
    if legacy_fim_run_dir:
        fim_run_parent = os.path.join(os.environ['HISTORICAL_FIM_RUN'], fim_run_dir)
    else:
        fim_run_parent = os.path.join(os.environ['outputDataDir'], fim_run_dir)
        
    assert os.path.exists(fim_run_parent), "Cannot locate " + fim_run_parent

    # Create paths to fim_run outputs for use in inundate().
    rem = os.path.join(fim_run_parent, 'rem_clipped_zeroed_masked.tif')
    
    catchments = os.path.join(fim_run_parent, 'gw_catchments_reaches_clipped_addedAttributes.tif')
    current_huc = test_id.split('_')[0]
    hucs, hucs_layerName = os.path.join(INPUTS_DIR, 'wbd', 'WBD_National.gpkg'), 'WBDHU8'
    hydro_table = os.path.join(fim_run_parent, 'hydroTable.csv')
    
    # Crosswalk feature_ids to hydroids.
    hydro_table_data = pd.read_csv(hydro_table, header=0)
    ht_feature_id_list = list(hydro_table_data.feature_id)
    ht_hydro_id_list = list(hydro_table_data.HydroID)
    lake_id_list = list(hydro_table_data.LakeID)
    
    # Get list of feature_ids_to_mask.    
    feature_ids_to_mask = []
    for f in range(0, len(lake_id_list)):
        if lake_id_list[f] != -999:
            lake_feature_id = ht_feature_id_list[f]
            if lake_feature_id not in feature_ids_to_mask:
                feature_ids_to_mask.append(lake_feature_id)

    # Remove duplicates and create list of hydro_ids to use as waterbody mask.
    reduced_ht_feature_id_list, reduced_ht_hydro_id_list, hydro_ids_to_mask = [], [], []

    for i in range(0, len(ht_hydro_id_list)):
        if ht_hydro_id_list[i] not in reduced_ht_hydro_id_list:
            reduced_ht_hydro_id_list.append(ht_hydro_id_list[i])
            reduced_ht_feature_id_list.append(ht_feature_id_list[i])
    print("Matching feature_ids...")
    for i in range(0, len(reduced_ht_feature_id_list)):
        ht_feature_id = reduced_ht_feature_id_list[i]
        ht_hydro_id = reduced_ht_hydro_id_list[i]
        if ht_feature_id in feature_ids_to_mask:
            hydro_ids_to_mask.append(ht_hydro_id)
            
    # Check if return interval is list of return intervals or single value.
    return_interval_list = return_interval
    if type(return_interval_list) != list:
        return_interval_list = [return_interval_list]
        
    for return_interval in return_interval_list:
        # Construct path to validation raster and forecast file.
        benchmark_category = test_id.split('_')[1]
        benchmark_raster_path = os.path.join(TEST_CASES_DIR, test_id, 'validation_data', return_interval, benchmark_category + '_huc_' + current_huc + '_inundation_extent_' + return_interval + '.tif')
        if not os.path.exists(benchmark_raster_path):  # Skip loop instance if the benchmark raster doesn't exist.
            continue
        
        # Construct paths to development test results if not existent.
        branch_test_case_dir = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'development_versions', branch_name, return_interval)
        if not os.path.exists(branch_test_case_dir):
            os.makedirs(branch_test_case_dir)
        
        # Define paths to inundation_raster and forecast file.
        inundation_raster = os.path.join(branch_test_case_dir, 'inundation_extent.tif')
        forecast = os.path.join(TEST_CASES_DIR, test_id, 'validation_data', return_interval, benchmark_category + '_huc_' + current_huc + '_flows_' + return_interval + '.csv')
    
        # Run inundate.
        print("Running inundation for " + return_interval + " for " + test_id + "...")
        inundate(
                 rem,catchments,hydro_table,forecast,hucs=hucs,hucs_layerName=hucs_layerName,subset_hucs=current_huc,
                 num_workers=1,aggregate=False,inundation_raster=inundation_raster,inundation_polygon=None,
                 depths=None,out_raster_profile=None,out_vector_profile=None,quiet=False
                )
   
        predicted_raster_path = os.path.join(os.path.split(inundation_raster)[0], os.path.split(inundation_raster)[1].replace('.tif', '_' + current_huc + '.tif'))  # The inundate adds the huc to the name so I account for that here.
    
        # Define outputs for agreement_raster, stats_json, and stats_csv.
        print("Comparing predicted inundation to benchmark inundation...")

        agreement_raster, stats_json, stats_csv = os.path.join(branch_test_case_dir, 'total_agreement.tif'), os.path.join(branch_test_case_dir, 'stats.json'), os.path.join(branch_test_case_dir, 'stats.csv')
            
        test_version_dictionary = compute_contingency_stats_from_rasters(predicted_raster_path, 
                                                                         benchmark_raster_path, 
                                                                         agreement_raster, 
                                                                         stats_csv=stats_csv, 
                                                                         stats_json=stats_json, 
                                                                         mask_values=hydro_ids_to_mask,
                                                                         stats_modes_list=stats_modes_list,
                                                                         test_id=test_id,
                                                                         )
        
        if compare_to_previous:
            print("Writing regression report...")
            text_block = []
            # Compare to previous stats files that are available.    
            archive_to_check = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'previous_versions')
            for stats_mode in stats_modes_list:
                archive_dictionary = profile_test_case_archive(archive_to_check, return_interval, stats_mode)
                
                # Create header for section.
                header = [stats_mode]
                for previous_version, paths in archive_dictionary.items():
                    header.append(previous_version)
                header.append(branch_name)
                text_block.append(header)
                
                # Loop through stats in SUMMARY_STATS for left.
                for stat in SUMMARY_STATS:
                    stat_line = [stat]
                    for previous_version, paths in archive_dictionary.items():
                        # Load stats for previous version.
                        previous_version_stats_json_path = paths['stats_json']
                        previous_version_stats_dict = json.load(open(previous_version_stats_json_path))
                        
                        # Append stat for the version to state_line.
                        stat_line.append(previous_version_stats_dict[stat])
                        
                    # Append stat for the current version to stat_line.
                    stat_line.append(test_version_dictionary[stats_mode][stat])

                    text_block.append(stat_line)
                    
                text_block.append([" "])
            
            regression_report_csv = os.path.join(branch_test_case_dir, 'stats_summary.csv')
            with open(regression_report_csv, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerows(text_block)
             
            print()
            print("--------------------------------------------------------------------------------------------------")
            ENDC = '\033[m'
            TGREEN_BOLD = '\033[32;1m'
            TGREEN = '\033[32m'
            TRED_BOLD = '\033[31;1m'
            TWHITE = '\033[37m'
            WHITE_BOLD = '\033[37;1m'
            CYAN_BOLD = '\033[36;1m'
            
            stats_mode = stats_modes_list[0]
            
            last_version_index = text_block[0].index('dev_latest')
            current_version_index = text_block[0].index(branch_name)
            
            for line in text_block:
                first_item = line[0]
                if first_item in stats_modes_list:
                    if first_item != stats_mode:  # Update the stats_mode and print a separator. 
                        print()
                        print()
                        print("--------------------------------------------------------------------------------------------------")
                    print()
                    stats_mode = first_item
                    print(CYAN_BOLD + stats_mode.upper().replace('_', ' ') + ": " + return_interval.upper(), ENDC)
                    print()
                
                    color = WHITE_BOLD
                    metric_name = '      '.center(len(max(SUMMARY_STATS, key=len)))
                    percent_change_header = '% CHG'
                    difference_header = 'DIFF'
                    current_version_header = line[current_version_index].upper()
                    last_version_header = line[last_version_index].upper()
                    # Print Header.
                    print(color + metric_name + "      " + percent_change_header.center((7)) + "       " + difference_header.center((15))  + "    " + current_version_header.center(18) + " " + last_version_header.center(18), ENDC)
                # Format and print stat row.
                elif first_item in SUMMARY_STATS:
                    stat_name = first_item.upper().center(len(max(SUMMARY_STATS, key=len))).replace('_', ' ')
                    current_version = round((line[current_version_index]), 3)
                    last_version = round((line[last_version_index]) + 0.000, 3)
                    difference = round(current_version - last_version, 3)
                    if difference > 0:
                        symbol = '+'
                        if first_item in GO_UP_STATS:
                            color = TGREEN_BOLD
                        elif first_item in GO_DOWN_STATS:
                            color = TRED_BOLD
                        else:
                            color = TWHITE
                    if difference < 0: 
                        symbol = '-'
                        if first_item in GO_UP_STATS:
                            color = TRED_BOLD
                        elif first_item in GO_DOWN_STATS:
                            color = TGREEN_BOLD
                        else:
                            color = TWHITE
                            
                    if difference == 0 : 
                        symbol, color = '+', TGREEN
                    percent_change = round((difference / last_version)*100,2)
                    
                    
                    print(WHITE_BOLD + stat_name + "     " + color + (symbol + " {:5.2f}".format(abs(percent_change)) + " %").rjust(len(percent_change_header)), ENDC + "    " + color + ("{:12.3f}".format((difference))).rjust(len(difference_header)), ENDC + "    " + "{:15.3f}".format(current_version).rjust(len(current_version_header)) + "   " + "{:15.3f}".format(last_version).rjust(len(last_version_header)) + "  ")
        
            print()
            print()
            print("--------------------------------------------------------------------------------------------------")
            print()
                            
        print(" ")
        print("Evaluation complete. All metrics for " + test_id + ", " + branch_name + ", " + return_interval + " are available at " + branch_test_case_dir)
        print(" ")
    
    if archive_results:
        print("Copying outputs to the 'previous_version' archive for " + test_id + "...")
        print()
        import shutil
        branch_name_dir = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'development_versions', branch_name, return_interval)
        destination_dir = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'previous_versions', branch_name, return_interval)
        
        print(branch_name_dir)
        print(destination_dir)
        
        shutil.copytree(branch_name_dir, destination_dir)
        

if __name__ == '__main__':
    
    # Parse arguments.
    parser = argparse.ArgumentParser(description='Inundation mapping and regression analysis for FOSS FIM. Regression analysis results are stored in the test directory.')
    parser.add_argument('-r','--fim-run-dir',help='Name of directory containing outputs of fim_run.sh',required=True)
    parser.add_argument('-b', '--branch-name',help='The name of the working branch in which features are being tested',required=True,default="")
    parser.add_argument('-t','--test-id',help='The test_id to use. Format as: HUC_BENCHMARKTYPE, e.g. 12345678_ble.',required=True,default="")
    parser.add_argument('-y', '--return-interval',help='The return interval to check. Options include: 100yr, 500yr',required=False,default=['10yr', '100yr', '500yr'])
    parser.add_argument('-c', '--compare-to-previous', help='Compare to previous versions of HAND.', required=False,action='store_true')
    parser.add_argument('-s', '--run-structure-stats', help='Create contingency stats at structures.', required=False,action='store_true')
    parser.add_argument('-a', '--archive-results', help='Automatically copy results to the "previous_version" archive for test_id. For admin use only.', required=False,action='store_true')
    parser.add_argument('-l','--legacy-fim-run-dir',help='If set, the -b argument name is redirected to historical fim_run output data dir.',required=False, action='store_true')
    
    # Extract to dictionary and assign to variables.
    args = vars(parser.parse_args())
    
    # TEMPORARY CODE
    if args['test_id'] != '12090301_ble':
        import sys
        print("Only the 12090301_ble test case is supported at this time. Additional benchmark data are being processed and will be added soon.")
        sys.exit()
    else:  
        run_alpha_test(**args)
