#!/usr/bin/env python3

import numpy as np
import pandas as pd
from tqdm import tqdm
from numba import njit, typeof, typed, types
#import concurrent.features 
import rasterio
import fiona
import shapely
from shapely.geometry import shape
from rasterio.mask import mask
from rasterio.io import DatasetReader,DatasetWriter
from rasterio.features import shapes,geometry_window
import argparse
import json


def inundate(rem,catchments,forecast,rating_curve,cross_walk,hucs,huc_level=6,
             num_workers=4,inundation_raster=None,inundation_polygon=None,depths=None):

    # make a catchment,stages numba dictionary
    catchmentStagesDict = __make_catchment_stages_dictionary(forecast,rating_curve,cross_walk)
    
    # input rem
    if isinstance(rem,str): 
        rem = rasterio.open(rem)
    elif isinstance(rem,DatasetReader):
        pass
    else:
        raise TypeError("Pass rasterio dataset or filepath for rem")

    # input catchments
    if isinstance(catchments,str):
        catchments = rasterio.open(catchments)
    elif isinstance(catchments,DatasetReader):
        pass
    else:
        raise TypeError("Pass rasterio dataset or filepath for catchments")

    # input hucs
    huc_level = str(huc_level)
    if isinstance(hucs,str):
        huc_layer = "WBDHU" + huc_level
        hucs = fiona.open(hucs,layer=huc_layer)
    elif isinstance(hucs,fiona.Collection):
        pass
    else:
        raise TypeError("Pass fiona collection or filepath for hucs")

    # save desired profiles for outputs
    depths_profile = rem.profile
    inundation_profile = catchments.profile

    # update output profiles
    depths_profile.update(driver= 'GTiff', blockxsize=256, blockysize=256, tiled=True, compress='lzw')
    inundation_profile.update(driver= 'GTiff',blockxsize=256, blockysize=256, tiled=True, compress='lzw')

    # open outputs
    if isinstance(depths,str): depths = rasterio.open(depths, "w", **depths_profile)
    if isinstance(inundation_raster,str): inundation_raster = rasterio.open(inundation_raster,"w",**inundation_profile)
    # find get polygon of aoi
    colName = 'HUC' + str(huc_level)
    for huc in hucs:
        if huc['properties'][colName] == '120903':
            aoi = shape(huc['geometry'])
            break 

    # mask out rem and catchments to aoi
    rem_window = geometry_window(rem,aoi)
    catchments_window = geometry_window(catchments,aoi)
    
    # load masks
    rem_mask = rem.read(1,window=rem_window)
    catchments_mask = catchments.read(1,window=catchments_window)
    
    # save desired mask shape
    desired_shape = rem.shape

    # flatten
    rem_mask = rem_mask.ravel()
    catchments_mask = catchments_mask.ravel()

    # create flat outputs
    depths_mask = rem_mask.copy()
    inundation_mask = catchments_mask.copy()

    # reset output values
    depths_mask[depths_mask != depths_profile['nodata']] = 0
    inundation_mask[inundation_mask != inundation_profile['nodata']] = -1

    inundation_mask,depths_mask = __go_fast_inundation(rem_mask,catchments_mask,catchmentStagesDict,inundation_mask,depths_mask)

    inundation_mask = inundation_mask.reshape(desired_shape)
    depths_mask = depths_mask.reshape(desired_shape)
    
    # write out inundation rasters
    if isinstance(inundation_raster,DatasetWriter): inundation_raster.write(inundation_mask,indexes=1,window=catchments_window)
    if isinstance(depths,DatasetWriter): depths.write(depths_mask,indexes=1,window=rem_window)

    # polygonize inundation
    if isinstance(inundation_polygon,str):
        inundation_polygon_json = shapes(inundation_raster,connectivity=8)
    
    #executor.done()
    # close datasets
    rem.close()
    catchments.close()
    hucs.close() 
    if isinstance(depths,DatasetWriter): depths.close()
    if isinstance(inundation_raster,DatasetWriter): inundation_raster.close()


@njit
def __go_fast_inundation(rem,catchments,catchmentStagesDict,inundation,depths):

    for i,(r,cm) in enumerate(zip(rem,catchments)):
        if cm in catchmentStagesDict:

            depth = catchmentStagesDict[cm] - r
            depths[i] = max(depth,0) # set negative depths to 0

            if depths[i] > 0 : # set positive depths to value of catchment in inundation
                inundation[i] = cm

    return(inundation,depths)


def __make_catchment_stages_dictionary(forecast_fileName,src_fileName,cross_walk_table_fileName):
    """ test """

    #print("Making catchment to stages numba dictionary")

    forecast = pd.read_csv(forecast_fileName, dtype={'feature_id' : int , 'discharge' : float})

    with open(src_fileName,'r') as f:
        src = json.load(f)

    cross_walk_table = pd.read_csv(cross_walk_table_fileName, dtype={'feature_id' : int , 'HydroID' : int})

    catchmentStagesDict = typed.Dict.empty(types.int32,types.float64)

    number_of_forecast_points = len(forecast)

    #for _,rows in tqdm(forecast.iterrows(),total=number_of_forecast_points):
    for _,rows in forecast.iterrows():
        discharge = rows['discharge']
        fid = int(rows['feature_id'])

        # discharge = rows[1]
        # fid = rows[0]
        matching_hydroIDs = cross_walk_table['HydroID'][cross_walk_table['feature_id'] == fid]

        for hid in matching_hydroIDs:

            stage_list = np.array(src[str(hid)]['stage_list'])
            q_list = np.array(src[str(hid)]['q_list'])
            indices_that_are_lower = list(q_list < discharge)

            # print(indices_that_are_lower)
            is_index_last = indices_that_are_lower[-1]

            if is_index_last:
                h = stage_list[-1]

                hid = types.int32(hid) ; h = types.float32(h)
                catchmentStagesDict[hid] = h

                continue

            index_of_lower = np.where(indices_that_are_lower)[0][-1]
            index_of_upper = index_of_lower + 1

            Q_lower = q_list[index_of_lower]
            h_lower = stage_list[index_of_lower]

            Q_upper = q_list[index_of_upper]
            h_upper = stage_list[index_of_upper]

            # linear interpolation
            h = h_lower + (discharge - Q_lower) * ((h_upper - h_lower) / (Q_upper - Q_lower))

            hid = types.int32(hid) ; h = types.float32(h)
            catchmentStagesDict[hid] = h

    return(catchmentStagesDict)


if __name__ == '__main__':

    # parse arguments
    parser = argparse.ArgumentParser(description='Inundation mapping for FOSS FIM')
    parser.add_argument('-r','--rem', help='REM raster at job level or mosaic vrt', required=True)
    parser.add_argument('-c','--catchments',help='Catchments raster at job level or mosaic vrt',required=True)
    parser.add_argument('-f','--forecast',help='Forecast discharges in CMS as CSV file',required=True)
    parser.add_argument('-s','--rating-curve',help='SRC JSON file',required=True)
    parser.add_argument('-w','--crosswalk',help='Cross-walk table csv',required=False,default=None)
    parser.add_argument('-b','--hucs',help='WBD datasets with HUC 4,6,8 layers',required=True)
    parser.add_argument('-l','--huc-level',help='HUC Level to inundate on',required=False,default=6)
    parser.add_argument('-j','--workers',help='Number of workers to run',required=False,default=6)
    parser.add_argument('-i','--inundation-raster',help='Inundation Raster output',required=False,default=None)
    parser.add_argument('-p','--inundation-polygon',help='Inundation polygon output',required=False,default=None)
    parser.add_argument('-d','--depths',help='Depths raster output',required=False,default=None)

    # extract to dictionary
    args = vars(parser.parse_args())
    
    #inundate(rem,catchments,forecast,rating_curve,cross_walk,hucs,huc_level=6,
    #         num_workers=4,inundation_raster=None,inundation_polygon=None,depths=None):
    # call function
    inundate( 
              rem = args['rem'], catchments = args['catchments'], forecast = args['forecast'],
              rating_curve = args['rating_curve'], cross_walk = args['crosswalk'],
              hucs = args['hucs'], huc_level = args['huc_level'],
              num_workers = args['workers'], inundation_raster = args['inundation_raster'],
              inundation_polygon = args['inundation_polygon'], depths = args['depths'], 
            )

    """
    inundation_mask_read.py -r ~/data/
    """
