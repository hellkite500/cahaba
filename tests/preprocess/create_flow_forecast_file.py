# -*- coding: utf-8 -*-
"""
Created on Wed Jul 29 11:48:37 2020
@author: Fernando Aristizabal with edits by Trevor Grout
"""
import os
import fiona
import geopandas as gpd
import argparse

def create_flow_forecast_file(ble_geodatabase, nwm_geodatabase, output_parent_dir, nwm_stream_layer_name = 'RouteLink_FL', nwm_feature_id_field ='ID'):
    '''
    This function will create a forecast flow file using ble data. It will select the ble XS layer (searching for 'XS' in layer name) and will intersect it with a nwm layer (searching for layer with 'fl'). It will the perform an intersection with the BLE XS layer and the nwm river layer. It will then calculate the median flow for the 100 and 500 year events for each nwm segment and convert flow from CFS to CMS. Individual forecast files (.csv) will be created  with two columns (nwm segment ID and Flow (CMS)) for the 100 year and the 500 year event. Flow field names are set to the default field names within the BLE submittal. As differing versions of the NWM river layer have different names for the ID field, this field will need to be specified as an argument to the function. Output flow forecast files will be automatically named to be compatible with current FIM code and will be written out in specific folder structures.

    Parameters
    ----------
    ble_geodatabase : STRING
        Path to BLE geodatabase.
    nwm_geodatabase : STRING
        Path to nwm geodatabase.
    output_parent_dir : STRING
        Output parent directory of output. Flow files will be output to subdirectories within parent directory.
    nwm_stream_layer_name : STRING 
       The stream centerline layer name (or partial layer name) for the NWM geodatabase.  Default is 'RouteLink_FL' (applicable if nwmv2.1 is used)
    nwm_feature_id_field : STRING 
       The feature id of the nwm segments.  Default is 'ID' (applicable if nwmv2.1 is used)
    Returns
    -------
    None.

    '''
    #Search for the layer that has 'XS' in the ble geodatabase. There should be only one and this is the 1D XS used in modeling. Read the layer into a geopandas dataframe.
    [xs_layer_name] = [i for i in fiona.listlayers(ble_geodatabase) if 'XS' in i]
    xs_layer = gpd.read_file(ble_geodatabase,layer = xs_layer_name)
    #Find HUC layer in ble geodatabase (search for "S_HUC") and retrieve the huc code (assumes only one huc per ble study).
    [huc_layer_name] = [i for i in fiona.listlayers(ble_geodatabase) if 'S_HUC' in i]
    huc_layer = gpd.read_file(ble_geodatabase, layer = huc_layer_name)
    [huc] = huc_layer['HUC_CODE'].unique()
    

    #Search for the layer that has nwm_stream_layer_name (default 'RouteLink_FL' from NWMv2.1) in the nwm geodatabase. Read in this layer using the bounding box option based on the extents of the BLE XS layer. According to geopandas documentation, "CRS mis-matches are resolved if given a GeoSeries or GeoDataFrame." The NWM layer is read in as a geopandas dataframe. 
    [nwm_layer_name] = [i for i in fiona.listlayers(nwm_geodatabase) if nwm_stream_layer_name in i]
    nwm_river_layer = gpd.read_file(nwm_geodatabase, bbox = xs_layer, layer = nwm_layer_name)
    
    #make sure xs_layer is in same projection as nwm_river_layer.
    xs_layer_proj = xs_layer.to_crs(nwm_river_layer.crs)
    
    #Perform an intersection of the BLE layers and the NWM layers, using the keep_geom_type set to False produces a point output.
    intersection = gpd.overlay(xs_layer_proj, nwm_river_layer, how = 'intersection', keep_geom_type = False)

    #Create the flow forecast files
    #define fields containing flow (typically these won't change for BLE)
    flow_fields = ['E_Q_01PCT','E_Q_0_2PCT']

    #define return period associated with flow_fields (in same order as flow_fields). These will also serve as subdirectory names.
    return_period = ['100yr','500yr']

    #Conversion factor from CFS to CMS
    dischargeMultiplier = 0.3048 ** 3 
        
    #Write individual flow csv files
    for i,flow in enumerate(flow_fields):

        #Write dataframe with just ID and single flow event
        forecast = intersection[[nwm_feature_id_field,flow]]

        #Rename field names and re-define datatypes
        forecast = forecast.rename(columns={nwm_feature_id_field :'feature_id',flow : 'discharge'})
        forecast = forecast.astype({'feature_id' : int , 'discharge' : float})

        #Calculate median flow per feature id
        forecast = forecast.groupby('feature_id').median()
        forecast = forecast.reset_index(level=0)

        #Convert CFS to CMS
        forecast['discharge'] = forecast['discharge'] * dischargeMultiplier

        #Set paths and write file
        output_dir = os.path.join(output_parent_dir, huc)
        dir_of_csv = os.path.join(output_dir,return_period[i])
        os.makedirs(dir_of_csv,exist_ok = True)
        path_to_csv = os.path.join(dir_of_csv,"ble_huc_{}_flows_{}.csv".format(huc,return_period[i]))
        forecast.to_csv(path_to_csv,index=False)   
   
if __name__ == '__main__':
    #Parse arguments
    parser = argparse.ArgumentParser(description = 'Produce forecast flow files from BLE datasets')
    parser.add_argument('-b', '--ble-geodatabase', help = 'BLE geodatabase (.gdb file extension). Will look for layer with "XS" in name. It is assumed the 100 year flow field is "E_Q_01PCT" and the 500 year flow field is "E_Q_0_2_PCT" as these are the default field names.', required = True)
    parser.add_argument('-n', '--nwm-geodatabase',  help = 'NWM geodatabase (.gdb file extension).', required = True)
    parser.add_argument('-o', '--output-parent-dir', help = 'Output directory where forecast files will be stored. Two subdirectories are created (100yr and 500yr) and in each subdirectory a forecast file is written', required = True)
    parser.add_argument('-l', '--nwm-stream-layer-name', help = 'NWM streams layer. Not required if NWM v2.1 is used (default layer is "RouteLink_FL")', required = False, default = 'RouteLink_FL')
    parser.add_argument('-f', '--nwm-feature-id-field', help = 'id field for nwm streams. Not required if NWM v2.1 is used (default id field is "ID")', required = False, default = 'ID')
    #Extract to dictionary and assign to variables.
    args = vars(parser.parse_args())
    #Run create_flow_forecast_file
    create_flow_forecast_file(**args)
    
    
