# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 13:10:51 2020

@author: bradford.bates
"""

import os

from run_test_case import run_alpha_test


TEST_CASES_DIR = r'/data/test_cases/'
PREVIOUS_FIM_DIR = r'/data/previous_fim'

if __name__ == '__main__':

    compare_to_previous = False
    
    test_cases_dir_list = os.listdir(TEST_CASES_DIR)
    
    previous_fim_list = os.listdir(PREVIOUS_FIM_DIR)
        
    for test_id in test_cases_dir_list:
        if 'validation' not in test_id:
            print("Backfilling " + test_id + "...")
                        
            for return_interval in ['100yr', '500yr']:
                print("---------> " + return_interval)
                current_huc = test_id.split('_')[0]
                if current_huc != '12090301':
                    continue
                
                for branch_name in previous_fim_list:
                    print(("---------> " + branch_name))
                    huc6 = test_id[:6]
                    
                    fim_run_dir = os.path.join(PREVIOUS_FIM_DIR, branch_name, huc6)
                    
                    # Make sure the performance archive and development archive are there.
                    performance_archive = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive')
                    additional_layers = os.path.join(TEST_CASES_DIR, test_id, 'additional_layers')
                    
                    if not os.path.exists(performance_archive):
                        os.mkdir(performance_archive)
                    if not os.path.exists(additional_layers):
                        os.mkdir(additional_layers)
                        
                    previous_versions = os.path.join(performance_archive, 'previous_versions')
                    development_versions = os.path.join(performance_archive, 'development_versions')
                    
                    if not os.path.exists(previous_versions):
                        os.mkdir(previous_versions)
                        
                    if not os.path.exists(development_versions):
                        os.mkdir(development_versions)
                    
                    branch_test_case_dir = os.path.join(TEST_CASES_DIR, test_id, 'performance_archive', 'previous_versions', branch_name, return_interval)
                    
                    print(("---------> Running alpha test..."))
                    run_alpha_test(fim_run_dir, branch_name, test_id, return_interval, compare_to_previous=False, run_structure_stats=False, archive_results=True, legacy_fim_run_dir=False, waterbody_mask_technique='nwm_100')
    
