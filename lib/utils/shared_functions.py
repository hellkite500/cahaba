# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 12:37:15 2020

@author: bradford.bates
"""

def pull_file(args):
    
    print("hey")
    url = args[0]
    full_pulled_filepath = args[1]
    print("there")
    
    print(url)
    print(full_pulled_filepath)
    
    import os
    import urllib.request
    
    print("Pulling " + url)
    if not(os.path.exists(full_pulled_filepath)):
        urllib.request.urlretrieve(url, full_pulled_filepath)