# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 12:37:15 2020

@author: bradford.bates
"""

def pull_file(url, full_pulled_filepath):
    
    import os
    import urllib.request
    
    print("Pulling " + url)
    
    if not(os.path.exists(full_pulled_filepath)):
    
        urllib.request.urlretrieve(url, full_pulled_filepath)