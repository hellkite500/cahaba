# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 13:10:51 2020

@author: bradford.bates
"""

import os

from run_test_case import run_alpha_test


TEST_CASES_DIR = r'/data/test_cases_backup/'
PREVIOUS_FIM_DIR = r'/data/previous_fim'

print(os.path.exists(TEST_CASES_DIR))

if __name__ == '__main__':

    compare_to_previous = False
    
    for test_id in ['12090301_ble']:
        print("Backfilling " + test_id + "...")
        
        for return_interval in ['100yr', '500yr']:
            print("---------> " + return_interval)
            current_huc = test_id.split('_')[0]
            
            for branch_name in ['fim_1_0_0', 'fim_2_0_0', 'fim_3_0_0']:
                print(("---------> " + branch_name))
                huc6 = test_id[:6]
                
                fim_run_dir = os.path.join(PREVIOUS_FIM_DIR, branch_name, huc6)
                
                branch_test_case_dir = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'previous_versions', branch_name, return_interval)
                
                inundation_raster = os.path.join(branch_test_case_dir, 'inundation_extent.tif')
                    
                # Construct path to validation raster and forecast file.
                benchmark_category = test_id.split('_')[1]
                benchmark_raster_path = os.path.join(TEST_CASES_DIR, test_id, 'validation_data', return_interval, benchmark_category + '_huc_' + current_huc + '_inundation_extent_' + return_interval + '.tif')
                forecast = os.path.join(TEST_CASES_DIR, test_id, 'validation_data', return_interval, benchmark_category + '_huc_' + current_huc + '_flows_' + return_interval + '.csv')
            
                predicted_raster_path = os.path.join(os.path.split(inundation_raster)[0], os.path.split(inundation_raster)[1].replace('.tif', '_' + current_huc + '.tif'))  # The inundate adds the huc to the name so I account for that here.
            
                # Define outputs for agreement_raster, stats_json, and stats_csv.
                agreement_raster, stats_json, stats_csv = os.path.join(branch_test_case_dir, 'agreement.tif'), os.path.join(branch_test_case_dir, 'stats.json'), os.path.join(branch_test_case_dir, 'stats.csv')

                print(("---------> Running alpha test..."))
                run_alpha_test(fim_run_dir, branch_name, test_id, return_interval, compare_to_previous=False)

                      
                print(" ")
                print("Completed. Stats outputs for " + test_id + " are in " + branch_test_case_dir)
                print(" ")