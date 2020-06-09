#!/bin/bash -e

# usgsProjection='+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m no_defs'

# works best
PROJ="+proj=aea +datum=NAD83 +x_0=0.0 +y_0=0.0 +lon_0=96dW +lat_0=23dN +lat_1=29d30'N +lat_2=45d30'N +towgs84=-0.9956000824677655,1.901299877314078,0.5215002840524426,0.02591500053005733,0.009425998542707753,0.01159900118427752,-0.00062000005129903 +no_defs +units=m"
nwmDir='/home/brian.avant/data/NWM2_1/CONUS/NWM_v2_1_Reservoirs_Final'
outputDataDir='/home/brian.avant/data/NWM2_1/CONUS'

# project nwm lakes
ogr2ogr -overwrite -progress -f GPKG $outputDataDir/nwm_lakes.gpkg $nwmDir/NWM_Reservoirs_v2_1_Final.shp -nln nwm_lakes
ogr2ogr -overwrite -progress -f GPKG -t_srs "$usgsProjection" $outputDataDir/nwm_lakes_proj.gpkg $outputDataDir/nwm_lakes.gpkg