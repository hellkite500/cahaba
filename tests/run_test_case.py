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
SUMMARY_STATS = ['csi', 'pod', 'far', 'true_negatives', 'false_negatives', 'true_positives', 'false_positives', 'percent_correct', 'bias', 'equitable_threat_score']


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
    

def run_alpha_test(fim_run_dir, branch_name, test_id, return_interval, compare_to_previous=False, run_structure_stats=False):
        
    stats_modes_list = ['total_area']
    if run_structure_stats: stats_modes_list.append('structures')
    
    # Get list of feature_ids_to_mask.
    lake_feature_id_csv = r'/data/pre_inputs/lake_feature_id.csv'  # This will be replaced by hydroTable
    
    feature_id_data = pd.read_csv(lake_feature_id_csv, header=0)
    feature_ids_to_mask = list(feature_id_data.ID)

    # Create paths to fim_run outputs for use in inundate().
    rem = os.path.join(fim_run_dir, 'rem_clipped_zeroed_masked.tif')
    catchments = os.path.join(fim_run_dir, 'gw_catchments_reaches_clipped_addedAttributes.tif')
    current_huc = test_id.split('_')[0]
    hucs, hucs_layerName = os.path.join(INPUTS_DIR, 'wbd', 'WBD_National.gpkg'), 'WBDHU8'
    hydro_table = os.path.join(fim_run_dir, 'hydroTable.csv')
    
    # Crosswalk feature_ids to hydroids.
    hydro_table_data = pd.read_csv(hydro_table, header=0)
    ht_feature_id_list = list(hydro_table_data.feature_id)
    ht_hydro_id_list = list(hydro_table_data.HydroID)
    
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
                 rem,catchments,forecast,hydro_table=hydro_table,hucs=hucs,hucs_layerName=hucs_layerName,
                 num_workers=1,inundation_raster=inundation_raster,inundation_polygon=None,depths=None,
                 out_raster_profile=None,out_vector_profile=None,aggregate=False,
                 current_huc=current_huc,__rating_curve=None,__cross_walk=None
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
#        from pprint import pprint
#        pprint(test_version_dictionary)
        
#        test_version_dictionary = {'structures': {'ACC': 0.9484586431653356,
#                'Bal_ACC': 0.7097991910302027,
#                'F1_score': 0.3877159309021113,
#                'FN_perc': 1.9737446066281097,
#                'FP_perc': 3.1803910768383368,
#                'MCC': 0.3654973953029118,
#                'NPV': 0.9792647172286089,
#                'PPV': 0.3391072109881725,
#                'TNR': 0.9670064684235788,
#                'TN_perc': 93.21399063618838,
#                'TPR': 0.45259191363682655,
#                'TP_perc': 1.6318736803451757,
#                'bias': 1.335,
#                'csi': 0.24,
#                'equitable_threat_score': 0.221,
#                'false_negatives': 5375,
#                'false_positives': 8661,
#                'far': 0.661,
#                'obsNegative_area': 2625060.0,
#                'obsNegative_perc': 0.9639438171302671,
#                'obsPositive_area': 98190.0,
#                'obsPositive_perc': 0.036056182869732854,
#                'percent_correct': 0.948,
#                'pod': 0.453,
#                'positiveDiff_area': 32860.0,
#                'positiveDiff_perc': 0.012066464702102271,
#                'predNegative_area': 2592200.0,
#                'predNegative_perc': 0.9518773524281648,
#                'predPositive_area': 131050.0,
#                'predPositive_perc': 0.048122647571835125,
#                'prevalence': 0.036056182869732854,
#                'total_area': 2723250.0,
#                'true_negatives': 253845,
#                'true_positives': 4444},
# 'total_area': {'ACC': 0.9099980914174687,
#                'Bal_ACC': 0.8236399271651511,
#                'F1_score': 0.7475766023583176,
#                'FN_perc': 6.218406554318853,
#                'FP_perc': 2.7817843039342773,
#                'MCC': 0.6982309025706909,
#                'NPV': 0.9258749372741192,
#                'PPV': 0.827317657927369,
#                'TNR': 0.9654239671845536,
#                'TN_perc': 77.67233600484654,
#                'TPR': 0.6818558871457487,
#                'TP_perc': 13.327473136900329,
#                'bias': 0.824,
#                'csi': 0.597,
#                'equitable_threat_score': 0.531,
#                'false_negatives': 3507375,
#                'false_positives': 1569013,
#                'far': 0.173,
#                'obsNegative_area': 453786300.0,
#                'obsNegative_perc': 0.8045412030878082,
#                'obsPositive_area': 110244850.0,
#                'obsPositive_perc': 0.1954587969121918,
#                'percent_correct': 0.91,
#                'pod': 0.682,
#                'positiveDiff_area': -19383620.0,
#                'positiveDiff_perc': -0.034366222503845745,
#                'predNegative_area': 473169920.0,
#                'predNegative_perc': 0.838907425591654,
#                'predPositive_area': 90861230.0,
#                'predPositive_perc': 0.16109257440834607,
#                'prevalence': 0.1954587969121918,
#                'total_area': 564031150.0,
#                'true_negatives': 43809617,
#                'true_positives': 7517110}}
        
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
            TGREEN = '\033[32;1m'
            TRED = '\033[31;1m'
            TWHITE = '\033[37m'
            WHITE_BOLD = '\033[37;1m'
            
            stats_mode = stats_modes_list[0]
            
            for line in text_block:
                first_item = line[0]
                if first_item in stats_modes_list:
                    if first_item != stats_mode:  # Update the stats_mode and print a separator. 
                        print()
                        print()
                        print("--------------------------------------------------------------------------------------------------")
                    print()
                    stats_mode = first_item
                    print(WHITE_BOLD + stats_mode.upper().replace('_', ' ') + ": " + return_interval.upper(), ENDC)
                    print()
                
                    color = WHITE_BOLD
                    metric_name = 'METRIC'.center(len(max(SUMMARY_STATS, key=len)))
                    percent_change_header = '% CHG'
                    difference_header = 'DIFF'
                    current_version_header = line[-1].upper()
                    last_version_header = line[-2].upper()
                    # Print Header.
                    print(color + metric_name + "      " + percent_change_header.center((7)) + "       " + difference_header.center((15))  + "    " + current_version_header.center(18) + " " + last_version_header.center(18), ENDC)
                # Format and print stat row.
                elif first_item in SUMMARY_STATS:
                    stat_name = first_item.upper().center(len(max(SUMMARY_STATS, key=len))).replace('_', ' ')
                    current_version = round((line[-1]), 3)
                    last_version = round((line[-2]) + 0.000, 3)
                    difference = round(current_version - last_version, 3)
                    if difference > 0:
                        symbol = '+'
                        if first_item in ['csi', 'pod', 'true_negatives', 'true_positives', 'percent_correct']:
                            color = TGREEN
                        elif first_item in ['far', 'false_negatives', 'false_positives', 'bias']:
                            color = TRED
                        else:
                            color = TWHITE
                    if difference < 0: 
                        symbol = '-'
                        if first_item in ['csi', 'pod', 'true_negatives', 'true_positives', 'percent_correct']:
                            color = TRED
                        elif first_item in ['far', 'false_negatives', 'false_positives', 'bias']:
                            color = TGREEN
                        else:
                            color = TWHITE
                            
                    if difference == 0 : 
                        symbol, color = '+', TWHITE
                    percent_change = round((difference / last_version)*100,2)
                    
                    
                    print(stat_name + "     " + color + (symbol + " {:5.2f}".format(abs(percent_change)) + " %").rjust(len(percent_change_header)), ENDC + "    " + color + ("{:12.3f}".format((difference))).rjust(len(difference_header)), ENDC + "    " + "{:15.3f}".format(current_version).rjust(len(current_version_header)) + "   " + "{:15.3f}".format(last_version).rjust(len(last_version_header)) + "  ")
        
            print()
            print()
            print("--------------------------------------------------------------------------------------------------")
            print()
                            
        print(" ")
        print("Evaluation complete. All metrics for " + test_id + ", " + branch_name + ", " + return_interval + " are available at " + os.path.join(branch_test_case_dir, return_interval))
        print(" ")
    

if __name__ == '__main__':
    
    # Parse arguments.
    parser = argparse.ArgumentParser(description='Inundation mapping and regression analysis for FOSS FIM. Regression analysis results are stored in the test directory.')
    parser.add_argument('-r','--fim-run-dir',help='Path to directory containing outputs of fim_run.sh',required=True)
    parser.add_argument('-b', '--branch-name',help='The name of the working branch in which features are being tested',required=True,default="")
    parser.add_argument('-t','--test-id',help='The test_id to use. Format as: HUC_BENCHMARKTYPE, e.g. 12345678_ble.',required=True,default="")
    parser.add_argument('-y', '--return-interval',help='The return interval to check. Options include: 100yr, 500yr',required=False,default=['10yr', '100yr', '500yr'])
    parser.add_argument('-c', '--compare-to-previous', help='Compare to previous versions of HAND.', required=False,action='store_true')
    parser.add_argument('-s', '--run-structure-stats', help='Create contingency stats at structures.', required=False,action='store_true')
    
    # Extract to dictionary and assign to variables.
    args = vars(parser.parse_args())
    
    # TEMPORARY CODE
    if args['test_id'] != '12090301_ble':
        import sys
        print("Only the 12090301_ble test case is supported at this time. Additional benchmark data are being processed and will be added soon.")
        sys.exit()
    else:  
        run_alpha_test(**args)
