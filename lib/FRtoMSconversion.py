'''----------------------------------------------------------------------------
 Tool Name:   FR to MS Network Conversion
 Source Name: FRtoMSconversion.py

 Inputs:    modelstreams
            NWMforecastpoint
            inletpoints
            nhddemFR
            fdrFR
Outputs:    modelstreamMS
            nhddemMSname                     
            fdrMSname                        
                              
 Description: Create model streams for RR approach and 7000 m buffer masked DEM and Fdr.
----------------------------------------------------------------------------'''

import sys
import os
import datetime
import argparse
import pandas as pd
import rasterio 
import geopandas as gpd

def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # script name + line number
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe())
    # Get Python syntax error
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

class ClassOp:
    def execute(self, parameters, messages):
        sOK = 'OK'
        spstart = "     "                                                  

        try:            
            modelstreams       = parameters[0]
            NWMforecastpoint   = parameters[1]
            inletpoints        = parameters[2]
            nhddemFR           = parameters[3]                  
            fdrFR              = parameters[4]    
            nhddemMSname       = parameters[5]                  
            fdrMSname          = parameters[6]              

            # create output layer names
            inFD = os.path.dirname(modelstreams)
            outGDB                   = os.path.dirname(inFD)                                             # define full gdb path
            outFolder                = os.path.join(os.path.dirname(outGDB), "Layers")                # define Layers folder name (for rasters)
            indem                    = os.path.join(outFolder, "nhddem")                         # define input dem raster - full extent and then reused for output buffered version
            infdr                    = os.path.join(outFolder, "fdrtpp")                         # define input flow direction raster - full extent and then reused for output buffered version
            
            # TODO: clean up projections - currently modelstreamMS outputs as USA_Contiguous_Albers_Equal_Area_Conic_USGS_version and rasters output as NAD_1983_Albers 
            sr = rasterio.open(nhddemFR).crs.to_epsg()
                        
            # tool constants
            floodAOIbuf = 7000 # "7000 METERS"
            
            # Identify origination points for AHPS and inlets and snap them onto ModelStream lines.
            print ("{}Using NWM forecast and inlet points".format(spstart))
            print ("              Appending NWM forecast and inlet points.")
            unsnapped_pts = gpd.read_file(outGDB, driver='FileGDB', layer=os.path.basename(NWMforecastpoint))
            inletpoints_gdb = gpd.read_file(outGDB, driver='FileGDB', layer=os.path.basename(inletpoints))
            if len(inletpoints_gdb) > 0:
                unsnapped_pts = unsnapped_pts.append(inletpoints_gdb)
            
            print ("              Snapping forecasting points to ModelStream and saving as {}.".format('snapped_points.shp'))
            modelstreams_gpd = gpd.read_file(outGDB, driver='FileGDB', layer=os.path.basename(modelstreams))
            modelstreams_union = modelstreams_gpd.geometry.unary_union
            
            snapped_geoms = []
            snappedpoints_df = pd.DataFrame(unsnapped_pts).drop(columns=['geometry', 'X_cor_', 'Y_cor_'])
            # snap lines to modelstream
            for i in range(len(unsnapped_pts)):
                snapped_geoms.append(modelstreams_union.interpolate(modelstreams_union.project(unsnapped_pts.geometry[i])))
            
            snappedpoints_df['geometry'] = snapped_geoms
            CRS = modelstreams_gpd.crs.to_epsg()
            snapped_points = gpd.GeoDataFrame(snappedpoints_df, crs = CRS)
            
            # get HydroID of modelstream segment that intersects with forecasting point
            print ("{}Building geometric network from ModelStream lines and creatinge RR ModelStream lines".format(spstart))
            print ("              Building GN from ModelStream.")
            modelstreamsID = modelstreams_gpd.filter(items=['HydroID', 'geometry'])
            # sjoin doesn't always return HydroIDs even though it is snapped; use the function below instead
            # snapped_pointswID = gpd.sjoin(snapped_points, modelstreamsID, how='left', op='intersects').drop(['index_right'], axis=1)
            def nearest_linestring(points, streamlines):
                idx = streamlines.geometry.distance(points).idxmin()
                return streamlines.loc[idx, 'HydroID']
            # this needs to be tested more to make sure it always gets the correct segment
            MSHydroIDs_list = snapped_points.geometry.apply(nearest_linestring, streamlines=modelstreamsID)
            snapped_points['HydroID'] = MSHydroIDs_list
            
            # Select only segments downstream of forecasting points; use NextDownID to trace network and subset MS stream network
            downstreamnetwork = modelstreams_gpd.filter(items=['HydroID', 'NextDownID'])
            downIDlist = []
            print ('Building MS network from {} forcasting points'.format(len(MSHydroIDs_list)))
            for startID in MSHydroIDs_list:
                print('Traversing network from HydroID {}'.format(startID))
                terminalID = downstreamnetwork.set_index('HydroID').loc[startID][0]
                downIDlist.append(startID)
                while terminalID != -1:
                    downIDlist.append(terminalID)
                    terminalID = downstreamnetwork.set_index('HydroID').loc[terminalID][0]
            print ('Removing duplicate HydroIDs')
            uniqueHydroIDs = set(downIDlist)
            MSnetwork = modelstreams_gpd[modelstreams_gpd['HydroID'].isin(uniqueHydroIDs)]
            
            # MSnetwork.to_file(os.path.join(inFD,'modelstreamMS.gdf',driver="FileGDB"))
            # MSnetwork.to_file(r'C:\Users\brian.avant\Documents\Hydrofabric\modelstreamMS.shp')
            
            # Limit the rasters to the buffer distance around the draft streams.
            print ("{}Limiting rasters to buffer area ({} meters) around model streams".format(spstart, str(floodAOIbuf)))
            print ("              Creating processing zone (buffer area).")
            MSnetwork_buffered = MSnetwork.unary_union.buffer(floodAOIbuf)
            # MSnetwork_buffered.to_file(r'C:\Users\brian.avant\Documents\Hydrofabric\MSnetwork_buffered.shp')
            
            # Mask nhddem
            import rasterio.mask
            with rasterio.open(nhddemFR) as src:
                out_image, out_transform = rasterio.mask.mask(src, [MSnetwork_buffered], crop=True)
                out_meta = src.meta
            
            out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})
            
            with rasterio.open(os.path.join(os.path.dirname(nhddemFR), nhddemMSname + '.tiff'), "w", **out_meta) as dest:
                dest.write(out_image)
            
            # Mask fdr
            with rasterio.open(fdrFR) as src:
                out_image, out_transform = rasterio.mask.mask(src, [MSnetwork_buffered], crop=True)
                out_meta = src.meta
            
            out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

            with rasterio.open(os.path.join(os.path.dirname(fdrFR), fdrMSname + '.tiff'), "w", **out_meta) as dest:
                dest.write(out_image)

        except:
            print (trace())
            sOK = 'NOTOK'
        return (sOK, indem, infdr)

if(__name__=='__main__'):
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("-p", "--parameters", nargs='+', default=[], required=True,   
                      help="list of parameters")
        args = ap.parse_args()
        modelstreams       = args.parameters[0]
        NWMforecastpoint   = args.parameters[1]
        inletpoints        = args.parameters[2]
        nhddemFR           = args.parameters[3]
        fdrFR              = args.parameters[4]
        nhddemMSname       = args.parameters[5]                  
        fdrMSname          = args.parameters[6]  
        
        oProcessor = ClassOp()
        parameters = (modelstreams, NWMforecastpoint, inletpoints, nhddemFR, nhddemFR, fdrFR, nhddemMSname, fdrMSname)
        tResults = None
        tResults = oProcessor.execute(parameters)

        if tResults[0] == 'OK':                    
                print (tResults)                    
                print ('Step 3 passed')
        else:
            print (tResults)
            print ('Step 3 failed')
            # sys.exit(0)
        del oProcessor
   
    except:
        print (trace())
        print (str(trace()))
    finally:
        dt2 = datetime.datetime.now()
        print ('Finished at ' + dt2.strftime("%Y-%m-%d %H:%M:%S"))