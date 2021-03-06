#!/bin/bash -e

## INITIALIZE TOTAL TIME TIMER ##
T_total_start

## SET OUTPUT DIRECTORY FOR UNIT ##
hucNumber="$1"
outputHucDataDir=$outputRunDataDir/$hucNumber
mkdir $outputHucDataDir

## SET VARIABLES AND FILE INPUTS ##
hucUnitLength=${#hucNumber}
huc4Identifier=${hucNumber:0:4}
huc2Identifier=${hucNumber:0:2}
input_NHD_WBHD_layer=WBDHU$hucUnitLength
input_DEM=$inputDataDir/nhdplus_rasters/HRNHDPlusRasters"$huc4Identifier"/elev_cm.tif
input_NLD=$inputDataDir/nld_vectors/huc2_levee_lines/nld_preprocessed_"$huc2Identifier".gpkg

## GET WBD ##
echo -e $startDiv"Get WBD $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/wbd.gpkg ] && \
ogr2ogr -f GPKG $outputHucDataDir/wbd.gpkg $input_WBD_gdb $input_NHD_WBHD_layer -where "HUC$hucUnitLength='$hucNumber'"
Tcount

## BUFFER WBD ##
echo -e $startDiv"Buffer WBD $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/wbd_buffered.gpkg ] && \
ogr2ogr -f GPKG -dialect sqlite -sql "select ST_buffer(geom, 5000) from 'WBDHU$hucUnitLength'" $outputHucDataDir/wbd_buffered.gpkg $outputHucDataDir/wbd.gpkg
Tcount

## GET STREAMS ##
echo -e $startDiv"Get Vector Layers and Subset $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/demDerived_reaches.shp ] && \
$libDir/snap_and_clip_to_nhd.py -d $hucNumber -w $input_NWM_Flows -f $input_NWM_Headwaters -s $input_NHD_Flowlines -l $input_NWM_Lakes -r $input_NLD -u $outputHucDataDir/wbd.gpkg -g $outputHucDataDir/wbd_buffered.gpkg -c $outputHucDataDir/NHDPlusBurnLineEvent_subset.gpkg -z $outputHucDataDir/nld_subset_levees.gpkg -a $outputHucDataDir/nwm_lakes_proj_subset.gpkg -t $outputHucDataDir/nwm_headwaters_proj_subset.gpkg -m $input_NWM_Catchments -n $outputHucDataDir/nwm_catchments_proj_subset.gpkg -e $outputHucDataDir/nhd_headwater_points_subset.gpkg -b $outputHucDataDir/nwm_subset_streams.gpkg
Tcount

## Clip WBD8 ##
echo -e $startDiv"Clip WBD8"$stopDiv
date -u
Tstart
ogr2ogr -f GPKG -clipsrc $outputHucDataDir/wbd_buffered.gpkg $outputHucDataDir/wbd8_clp.gpkg $inputDataDir/wbd/WBD_National.gpkg WBDHU8
Tcount

## CLIP DEM ##
echo -e $startDiv"Clip DEM $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/dem.tif ] && \
gdalwarp -cutline $outputHucDataDir/wbd_buffered.gpkg -crop_to_cutline -ot Int32 -r bilinear -of "GTiff" -overwrite -co "BLOCKXSIZE=512" -co "BLOCKYSIZE=512" -co "TILED=YES" -co "COMPRESS=LZW" -co "BIGTIFF=YES" $input_DEM $outputHucDataDir/dem.tif
Tcount

## GET RASTER METADATA
echo -e $startDiv"Get DEM Metadata $hucNumber"$stopDiv
date -u
Tstart
read fsize ncols nrows ndv xmin ymin xmax ymax cellsize_resx cellsize_resy<<<$($libDir/getRasterInfoNative.py $outputHucDataDir/dem.tif)
Tcount

## RASTERIZE NLD POLYLINES ##
echo -e $startDiv"Rasterize all NLD polylines using zelev vertices"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/nld_rasterized_elev.tif ] && [ -f $outputHucDataDir/nld_subset_levees.gpkg ] && \
gdal_rasterize -l nld_subset_levees -3d -at -init $ndv -te $xmin $ymin $xmax $ymax -ts $ncols $nrows -ot Float32 -of GTiff -co "COMPRESS=LZW" -co "BIGTIFF=YES" -co "TILED=YES" $outputHucDataDir/nld_subset_levees.gpkg $outputHucDataDir/nld_rasterized_elev.tif
Tcount

## CONVERT TO METERS ##
echo -e $startDiv"Convert DEM to Meters $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/dem_meters.tif ] && \
gdal_calc.py --quiet --type=Float32 --co "BLOCKXSIZE=512" --co "BLOCKYSIZE=512" --co "TILED=YES" --co "COMPRESS=LZW" --co "BIGTIFF=YES" -A $outputHucDataDir/dem.tif --outfile="$outputHucDataDir/dem_meters.tif" --calc="A/100" --NoDataValue=$ndv
Tcount

## RASTERIZE REACH BOOLEAN (1 & 0) ##
echo -e $startDiv"Rasterize Reach Boolean $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/flows_grid_boolean.tif ] && \
gdal_rasterize -ot Int32 -burn 1 -init 0 -co "COMPRESS=LZW" -co "BIGTIFF=YES" -co "TILED=YES" -te $xmin $ymin $xmax $ymax -ts $ncols $nrows $outputHucDataDir/NHDPlusBurnLineEvent_subset.gpkg $outputHucDataDir/flows_grid_boolean.tif
Tcount

## RASTERIZE NHD HEADWATERS (1 & 0) ##
echo -e $startDiv"Rasterize NHD Headwaters $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/headwaters.tif ] && \
gdal_rasterize -ot Int32 -burn 1 -init 0 -co "COMPRESS=LZW" -co "BIGTIFF=YES" -co "TILED=YES" -te $xmin $ymin $xmax $ymax -ts $ncols $nrows $outputHucDataDir/nhd_headwater_points_subset.gpkg $outputHucDataDir/headwaters.tif
Tcount

# RASTERIZE NWM CATCHMENTS ##
echo -e $startDiv"Raster NWM Catchments $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/nwm_catchments_proj_subset.tif ] && \
gdal_rasterize -ot Int32 -a ID -a_nodata 0 -init 0 -co "COMPRESS=LZW" -co "BIGTIFF=YES" -co "TILED=YES" -te $xmin $ymin $xmax $ymax -ts $ncols $nrows $outputHucDataDir/nwm_catchments_proj_subset.gpkg $outputHucDataDir/nwm_catchments_proj_subset.tif
Tcount

## BURN LEVEES INTO DEM ##
echo -e $startDiv"Burn nld levees into dem & convert nld elev to meters (*Overwrite dem_meters.tif output) $hucNumber"$stopDiv
date -u
Tstart
[ -f $outputHucDataDir/nld_rasterized_elev.tif ] && \
gdal_calc.py --quiet --type=Float32 --overwrite --NoDataValue $ndv --co "BLOCKXSIZE=512" --co "BLOCKYSIZE=512" --co "TILED=YES" --co "COMPRESS=LZW" --co "BIGTIFF=YES" -A $outputHucDataDir/dem_meters.tif -B $outputHucDataDir/nld_rasterized_elev.tif --outfile="$outputHucDataDir/dem_meters.tif" --calc="maximum(A,(B*0.3048))" --NoDataValue=$ndv
Tcount

## BURN NEGATIVE ELEVATIONS STREAMS ##
echo -e $startDiv"Drop thalweg elevations by "$negativeBurnValue" units $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/dem_burned.tif ] && \
gdal_calc.py --quiet --type=Float32 --overwrite --co "COMPRESS=LZW" --co "BIGTIFF=YES" --co "TILED=YES" -A $outputHucDataDir/dem_meters.tif -B $outputHucDataDir/flows_grid_boolean.tif --calc="A-$negativeBurnValue*B" --outfile="$outputHucDataDir/dem_burned.tif" --NoDataValue=$ndv
Tcount

## PIT REMOVE BURNED DEM ##
echo -e $startDiv"Pit remove Burned DEM $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/dem_burned_filled.tif ] && \
rd_depression_filling $outputHucDataDir/dem_burned.tif $outputHucDataDir/dem_burned_filled.tif
Tcount

## D8 FLOW DIR ##
echo -e $startDiv"D8 Flow Directions on Burned DEM $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/flowdir_d8_burned_filled.tif ] && \
mpiexec -n $ncores_fd $taudemDir2/d8flowdir -fel $outputHucDataDir/dem_burned_filled.tif -p $outputHucDataDir/flowdir_d8_burned_filled.tif
Tcount

## MASK BURNED DEM FOR STREAMS ONLY ###
echo -e $startDiv"Mask Burned DEM for Thalweg Only $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/flowdir_d8_burned_filled_flows.tif ] && \
gdal_calc.py --quiet --type=Int32 --overwrite --co "COMPRESS=LZW" --co "BIGTIFF=YES" --co "TILED=YES" -A $outputHucDataDir/flowdir_d8_burned_filled.tif -B $outputHucDataDir/flows_grid_boolean.tif --calc="A/B" --outfile="$outputHucDataDir/flowdir_d8_burned_filled_flows.tif" --NoDataValue=0
Tcount

## FLOW CONDITION STREAMS ##
echo -e $startDiv"Flow Condition Thalweg $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/dem_thalwegCond.tif ] && \
$taudemDir/flowdircond -p $outputHucDataDir/flowdir_d8_burned_filled_flows.tif -z $outputHucDataDir/dem_meters.tif -zfdc $outputHucDataDir/dem_thalwegCond.tif
Tcount

## D8 SLOPES ##
echo -e $startDiv"D8 Slopes from DEM $hucNumber"$stopDiv
date -u
Tstart
mpiexec -n $ncores_fd $taudemDir2/d8flowdir -fel $outputHucDataDir/dem_meters.tif -sd8 $outputHucDataDir/slopes_d8_dem_meters.tif
Tcount

## DINF FLOW DIR ##
# echo -e $startDiv"DINF on Filled Thalweg Conditioned DEM"$stopDiv
# date -u
# Tstart
# [ ! -f $outputHucDataDir/flowdir_dinf_thalwegCond.tif] && \
# mpiexec -n $ncores_fd $taudemDir2/dinfflowdir -fel $outputHucDataDir/dem_thalwegCond_filled.tif -ang $outputHucDataDir/flowdir_dinf_thalwegCond.tif -slp $outputHucDataDir/slopes_dinf.tif
# Tcount

## D8 FLOW ACCUMULATIONS ##
echo -e $startDiv"D8 Flow Accumulations $hucNumber"$stopDiv
date -u
Tstart
$taudemDir/aread8 -p $outputHucDataDir/flowdir_d8_burned_filled.tif -ad8  $outputHucDataDir/flowaccum_d8_burned_filled.tif -wg  $outputHucDataDir/headwaters.tif -nc
Tcount

# THRESHOLD ACCUMULATIONS ##
echo -e $startDiv"Threshold Accumulations $hucNumber"$stopDiv
date -u
Tstart
$taudemDir/threshold -ssa $outputHucDataDir/flowaccum_d8_burned_filled.tif -src  $outputHucDataDir/demDerived_streamPixels.tif -thresh 1
Tcount

# STREAMNET FOR REACHES ##
echo -e $startDiv"Stream Net for Reaches $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/demDerived_reaches.shp ] && \
$taudemDir/streamnet -p $outputHucDataDir/flowdir_d8_burned_filled.tif -fel $outputHucDataDir/dem_thalwegCond.tif -ad8 $outputHucDataDir/flowaccum_d8_burned_filled.tif -src $outputHucDataDir/demDerived_streamPixels.tif -ord $outputHucDataDir/streamOrder.tif -tree $outputHucDataDir/treeFile.txt -coord $outputHucDataDir/coordFile.txt -w $outputHucDataDir/sn_catchments_reaches.tif -net $outputHucDataDir/demDerived_reaches.shp
Tcount

## SPLIT DERIVED REACHES ##
echo -e $startDiv"Split Derived Reaches $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/demDerived_reaches_split.gpkg ] && \
$libDir/split_flows.py $outputHucDataDir/demDerived_reaches.shp $outputHucDataDir/dem_thalwegCond.tif $outputHucDataDir/demDerived_reaches_split.gpkg $outputHucDataDir/demDerived_reaches_split_points.gpkg $maxSplitDistance_meters $slope_min $outputHucDataDir/wbd8_clp.gpkg  $outputHucDataDir/nwm_lakes_proj_subset.gpkg
Tcount

## GAGE WATERSHED FOR REACHES ##
echo -e $startDiv"Gage Watershed for Reaches $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/gw_catchments_reaches.tif ] && \
mpiexec -n $ncores_gw $taudemDir/gagewatershed -p $outputHucDataDir/flowdir_d8_burned_filled.tif -gw $outputHucDataDir/gw_catchments_reaches.tif -o $outputHucDataDir/demDerived_reaches_split_points.gpkg -id $outputHucDataDir/idFile.txt
Tcount

## VECTORIZE FEATURE ID CENTROIDS ##
echo -e $startDiv"Vectorize Pixel Centroids $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/flows_points_pixels.gpkg ] && \
$libDir/reachID_grid_to_vector_points.py $outputHucDataDir/demDerived_streamPixels.tif $outputHucDataDir/flows_points_pixels.gpkg featureID
Tcount

## GAGE WATERSHED FOR PIXELS ##
echo -e $startDiv"Gage Watershed for Pixels $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/gw_catchments_pixels.tif ] && \
mpiexec -n $ncores_gw $taudemDir/gagewatershed -p $outputHucDataDir/flowdir_d8_burned_filled.tif -gw $outputHucDataDir/gw_catchments_pixels.tif -o $outputHucDataDir/flows_points_pixels.gpkg -id $outputHucDataDir/idFile.txt
Tcount

# D8 REM ##
echo -e $startDiv"D8 REM $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/rem.tif ] && \
$libDir/rem.py -d $outputHucDataDir/dem_thalwegCond.tif -w $outputHucDataDir/gw_catchments_pixels.tif -o $outputHucDataDir/rem.tif
Tcount

## DINF DISTANCE DOWN ##
# echo -e $startDiv"DINF Distance Down on Filled Thalweg Conditioned DEM $hucNumber"$stopDiv
# date -u
# Tstart
# [ ! -f $outputHucDataDir/flowdir_dinf_thalwegCond.tif] && \
# mpiexec -n $ncores_fd $taudemDir/dinfdistdown -ang $outputHucDataDir/flowdir_dinf_thalwegCond.tif -fel $outputHucDataDir/dem_thalwegCond_filled.tif -src $outputHucDataDir/demDerived_streamPixels.tif -dd $outputHucDataDir/rem.tif -m ave h
# Tcount

## BRING DISTANCE DOWN TO ZERO ##
echo -e $startDiv"Zero out negative values in distance down grid $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/rem_zeroed.tif ] && \
gdal_calc.py --quiet --type=Float32 --overwrite --co "COMPRESS=LZW" --co "BIGTIFF=YES" --co "TILED=YES" -A $outputHucDataDir/rem.tif --calc="(A*(A>=0))+((A<=$ndv)*$ndv)" --NoDataValue=$ndv --outfile=$outputHucDataDir/"rem_zeroed.tif"
Tcount

## POLYGONIZE REACH WATERSHEDS ##
echo -e $startDiv"Polygonize Reach Watersheds $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/gw_catchments_reaches.gpkg ] && \
gdal_polygonize.py -8 -f GPKG $outputHucDataDir/gw_catchments_reaches.tif $outputHucDataDir/gw_catchments_reaches.gpkg catchments HydroID
Tcount

## PROCESS CATCHMENTS AND MODEL STREAMS STEP 1 ##
echo -e $startDiv"Process catchments and model streams step 1 $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.gpkg ] && \
$libDir/filter_catchments_and_add_attributes.py $outputHucDataDir/gw_catchments_reaches.gpkg $outputHucDataDir/demDerived_reaches_split.gpkg $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.gpkg $outputHucDataDir/demDerived_reaches_split_filtered.gpkg $outputHucDataDir/wbd8_clp.gpkg $hucNumber
Tcount

## GET RASTER METADATA ##
echo -e $startDiv"Get Clipped Raster Metadata $hucNumber"$stopDiv
date -u
Tstart
read fsize ncols nrows ndv_clipped xmin ymin xmax ymax cellsize_resx cellsize_resy<<<$($libDir/getRasterInfoNative.py $outputHucDataDir/gw_catchments_reaches.tif)
Tcount

## RASTERIZE NEW CATCHMENTS AGAIN ##
echo -e $startDiv"Rasterize filtered catchments $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.tif ] && \
gdal_rasterize -ot Int32 -a HydroID -a_nodata 0 -init 0 -co "COMPRESS=LZW" -co "BIGTIFF=YES" -co "TILED=YES" -te $xmin $ymin $xmax $ymax -ts $ncols $nrows $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.gpkg $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.tif
Tcount

## MASK SLOPE RASTER ##
echo -e $startDiv"Masking Slope Raster to HUC $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/slopes_d8_dem_meters_masked.tif ] && \
gdal_calc.py --quiet --type=Float32 --overwrite --co "COMPRESS=LZW" --co "BIGTIFF=YES" --co "TILED=YES" -A $outputHucDataDir/slopes_d8_dem_meters.tif -B $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.tif --calc="(A*(B>0))+((B<=0)*-1)" --NoDataValue=-1 --outfile=$outputHucDataDir/"slopes_d8_dem_meters_masked.tif"
Tcount

## MASK REM RASTER ##
echo -e $startDiv"Masking REM Raster to HUC $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/rem_zeroed_masked.tif ] && \
gdal_calc.py --quiet --type=Float32 --overwrite --co "COMPRESS=LZW" --co "BIGTIFF=YES" --co "TILED=YES" -A $outputHucDataDir/rem_zeroed.tif -B $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.tif --calc="(A*(B>0))+((B<=0)*$ndv)" --NoDataValue=$ndv --outfile=$outputHucDataDir/"rem_zeroed_masked.tif"
Tcount

## MAKE CATCHMENT AND STAGE FILES ##
echo -e $startDiv"Generate Catchment List and Stage List Files $hucNumber"$stopDiv
date -u
Tstart
$libDir/make_stages_and_catchlist.py $outputHucDataDir/demDerived_reaches_split_filtered.gpkg $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.gpkg $outputHucDataDir/stage.txt $outputHucDataDir/catchment_list.txt $stage_min_meters $stage_interval_meters $stage_max_meters
Tcount

## HYDRAULIC PROPERTIES ##
echo -e $startDiv"Hydraulic Properties $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/src_base.csv ] && \
$taudemDir/catchhydrogeo -hand $outputHucDataDir/rem_zeroed_masked.tif -catch $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.tif -catchlist $outputHucDataDir/catchment_list.txt -slp $outputHucDataDir/slopes_d8_dem_meters_masked.tif -h $outputHucDataDir/stage.txt -table $outputHucDataDir/src_base.csv
Tcount

## GET MAJORITY COUNTS ##
echo -e $startDiv"Getting majority counts $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/majority.geojson ] && \
fio cat $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.gpkg | rio zonalstats -r $outputHucDataDir/nwm_catchments_proj_subset.tif --stats majority > $outputHucDataDir/majority.geojson
Tcount

## FINALIZE CATCHMENTS AND MODEL STREAMS ##
echo -e $startDiv"Finalize catchments and model streams $hucNumber"$stopDiv
date -u
Tstart
[ ! -f $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes_crosswalked.gpkg ] && \
$libDir/add_crosswalk.py $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes.gpkg $outputHucDataDir/demDerived_reaches_split_filtered.gpkg $outputHucDataDir/src_base.csv $outputHucDataDir/majority.geojson $outputHucDataDir/gw_catchments_reaches_filtered_addedAttributes_crosswalked.gpkg $outputHucDataDir/demDerived_reaches_split_filtered_addedAttributes_crosswalked.gpkg $outputHucDataDir/src_full_crosswalked.csv $outputHucDataDir/src.json $outputHucDataDir/crosswalk_table.csv $outputHucDataDir/hydroTable.csv $outputHucDataDir/wbd8_clp.gpkg $outputHucDataDir/nwm_subset_streams.gpkg $manning_n
Tcount
