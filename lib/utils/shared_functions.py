# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 12:37:15 2020

@author: bradford.bates
"""

import os


def pull_file(url, full_pulled_filepath):
    
    import urllib.request
    
    print("Pulling " + url)
    urllib.request.urlretrieve(url, full_pulled_filepath)

        
def run_system_command(args):
    
    command = args[0]
    os.system(command)
    