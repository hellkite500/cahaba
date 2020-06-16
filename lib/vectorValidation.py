#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geopandas as gpd
import pandas as pd
import numpy as np
import argparse
from os.path import splitext
from collections import OrderedDict
from tqdm import tqdm
from shapely.geos import TopologicalError
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection, mapping, shape
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import as_completed
import warnings


class VectorValidation:

	@classmethod
	def binaryEvaluation(cls,predicted_fileName,validation_fileName,analysisExtents_fileName,
						exclusionMask_fileName=None,output_map_fileName=None,output_statistics_fileName=None,
						split_threshold_meters=2000,simplify_tolerance_meters=10,verbose=False,fishnetThreshold=None):

		""" Ensure both predicted and validation files have been clipped to analysis extents."""

		pd.set_option('display.max_rows', None)

		if fishnetThreshold is not None:
			warnings.simplefilter('always')
			warnings.warn("Deprecated use of fishnetThreshold, please use split_threshold_meter parameter instead",DeprecationWarning)
			fishnetThreshold = split_threshold_meters

		#####################################################################################
		############### import files #########################
		#####################################################################################
		if verbose:
			print("Loading files ...")
		# predicted = gpd.read_file(predicted_fileName)
		# validation = gpd.read_file(validation_fileName)
		# extents = gpd.read_file(analysisExtents_fileName)
		# if exclusionMask_fileName is not None:
			# exclusionMask = gpd.read_file(exclusionMask_fileName)

		with ThreadPoolExecutor(max_workers=4) as executor:

			args = [predicted_fileName, validation_fileName, analysisExtents_fileName]

			if exclusionMask_fileName is not None:
				args = args + [exclusionMask_fileName]

			results = []

			for arg in args:
				result = executor.submit(gpd.read_file, arg)
				results = results + [result]

			predicted = results[0].result() ;  validation = results[1].result() ; extents = results[2].result()

			if len(results) == 4:
				exclusionMask = results[3].result()

			del results,result

		#####################################################################################
		####### project to equal area #######
		#####################################################################################
		if verbose:
			print("Projecting files ...")
		projection = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'
		# predicted = predicted.to_crs(projection)
		# validation = validation.to_crs(projection)
		# extents = extents.to_crs(projection)
		# if exclusionMask_fileName is not None:
		# 	exclusionMask = exclusionMask.to_crs(projection)

		with ThreadPoolExecutor(max_workers=4) as executor:

			arguments = {
							'predicted' : [predicted.to_crs, projection],
							'validation' : [validation.to_crs, projection],
							'extents' : [extents.to_crs, projection]
						}

			if exclusionMask_fileName is not None:
				arguments['exclusionMask'] = [exclusionMask.to_crs,projection]

			processes = {executor.submit(*argument) : name for name,argument in arguments.items()}

			for f in as_completed(processes):

				if verbose:
					print("\t{} completed".format(processes[f]))

				if processes[f] == 'predicted':
					predicted = f.result()

				if processes[f] == 'validation':
					validation = f.result()

				if processes[f] == 'extents':
					extents = f.result()

				if exclusionMask_fileName is not None:
					if processes[f] == 'exclusionMask':
						exclusionMask = f.result()

		#####################################################################################
		############ simplify geometries #############
		#####################################################################################
		if simplify_tolerance_meters != 0:
			if verbose:
				print("Simplifying geometries ...")


			with ThreadPoolExecutor(max_workers=4) as executor:

				arguments = {
								'predicted' : [predicted, simplify_tolerance_meters],
								'validation' : [validation, simplify_tolerance_meters],
								'extents' : [extents, simplify_tolerance_meters]
							}

				if exclusionMask_fileName is not None:
					arguments['exclusionMask'] = [exclusionMask,simplify_tolerance_meters]

				processes = {executor.submit(VectorValidation.__simplifyGeoDataFrame,*argument) : name for name,argument in arguments.items()}

				for f in as_completed(processes):

					if verbose:
						print("\t{} completed".format(processes[f]))

					if processes[f] == 'predicted':
						predicted = f.result()

					if processes[f] == 'validation':
					 	validation = f.result()

					if processes[f] == 'extents':
						extents = f.result()

					if exclusionMask_fileName is not None:
						if processes[f] == 'exclusionMask':
							exclusionMask = f.result()

		#####################################################################################
		############ explode #############
		#####################################################################################
		print('Exploding and reseting indices ...')
		predicted = predicted.explode().reset_index(level=1,drop=True)
		validation = validation.explode().reset_index(level=1,drop=True)
		extents = extents.explode().reset_index(level=1,drop=True)
		if exclusionMask_fileName is not None:
			exclusionMask = exclusionMask.explode().reset_index(level=1,drop=True)

		#####################################################################################
		######### Fix Geometries #########
		#####################################################################################
		# print('Fixing geometries ...')
		# predicted.geometry = VectorValidation.__fixGeometries(predicted.geometry)
		# validation.geometry = VectorValidation.__fixGeometries(validation.geometry)
		# extents.geometry = VectorValidation.__fixGeometries(extents.geometry)
		# if exclusionMask_fileName is not None:
			# exclusionMask.geometry = VectorValidation.__fixGeometries(exclusionMask.geometry)

		if verbose:
			print("Fixing geometries ...")


		with ThreadPoolExecutor(max_workers=4) as executor:

			arguments = {
							'predicted' : [predicted.geometry],
							'validation' : [validation.geometry],
							'extents' : [extents.geometry]
						}

			if exclusionMask_fileName is not None:
				arguments['exclusionMask'] = [exclusionMask.geometry]

			processes = {executor.submit(VectorValidation.__fixGeometries,*argument) : name for name,argument in arguments.items()}

			for f in as_completed(processes):

				if verbose:
					print("\t{} completed".format(processes[f]))

				if processes[f] == 'predicted':
					predicted = f.result()

				if processes[f] == 'validation':
					validation = f.result()

				if processes[f] == 'extents':
					extents = f.result()

				if exclusionMask_fileName is not None:
					if processes[f] == 'exclusionMask':
						exclusionMask = f.result()

		#####################################################################################
		############# Splitting #############
		#####################################################################################
		if split_threshold_meters is not None:
			if verbose:
				print('Splitting files ...')
				"""
				print('predicted ...')

			predicted = VectorValidation.__katanaGeoDataFrame(predicted,split_threshold_meters)
			if verbose:
				print('validation ... ')
			validation = VectorValidation.__katanaGeoDataFrame(validation,split_threshold_meters)

			if verbose:
				print('extents ...')
			extents = VectorValidation.__katanaGeoDataFrame(extents,split_threshold_meters)

			if exclusionMask_fileName is not None:
				if verbose:
					print('exclusion mask ...')
				exclusionMask = VectorValidation.__katanaGeoDataFrame(exclusionMask,split_threshold_meters)
			"""

			with ThreadPoolExecutor(max_workers=4) as executor:

				arguments = {
								'predicted' : [predicted, split_threshold_meters,verbose],
								'validation' : [validation, split_threshold_meters,verbose],
								'extents' : [extents, split_threshold_meters,verbose]
							}

				if exclusionMask_fileName is not None:
					arguments['exclusionMask'] = [exclusionMask,split_threshold_meters,verbose]

				processes = { executor.submit(VectorValidation.__fishnetGeoDataFrame,*argument) : name for name,argument in arguments.items() }

				for f in as_completed(processes):

					if verbose:
						print("\t{} completed".format(processes[f]))

					if processes[f] == 'predicted':
						predicted = f.result()

					if processes[f] == 'validation':
					 	validation = f.result()

					if processes[f] == 'extents':
						extents = f.result()

					if exclusionMask_fileName is not None:
						if processes[f] == 'exclusionMask':
							exclusionMask = f.result()

		#####################################################################################
		### remove exclusion mask from extents and clip predicted and validation ###
		#####################################################################################
		if exclusionMask_fileName is not None:

			if verbose:
				print('Removing exclusion mask from extents ...')

			extents = gpd.overlay(extents,exclusionMask,how='difference')
			extents = extents.explode().reset_index(level=1,drop=True)

		#####################################################################################
		######## clip predicted and validation to extents ############
		#####################################################################################
		if verbose:
			print('Clipping predicted and validation by extents ... ')

		predicted = gpd.overlay(predicted,extents,how='intersection')
		validation = gpd.overlay(validation,extents,how='intersection')

		#####################################################################################
		### reexplode again just to avoid non-noded intersection issues ###
		#####################################################################################
		predicted = predicted.explode()
		validation = validation.explode()
		extents = extents.explode()
		if exclusionMask_fileName is not None:
			exclusionMask = exclusionMask.explode()

		#####################################################################################
		################ round precisons ################
		#####################################################################################
		predicted.geometry = predicted.geometry.apply(lambda x: VectorValidation.__roundGeometry(x,4))
		validation.geometry = validation.geometry.apply(lambda x: VectorValidation.__roundGeometry(x,4))
		extents.geometry = extents.geometry.apply(lambda x: VectorValidation.__roundGeometry(x,4))
		if exclusionMask_fileName is not None:
			exclusionMask.geometry = exclusionMask.geometry.apply(lambda x: VectorValidation.__roundGeometry(x,4))

		#####################################################################################
		######### Fix Geometries #########
		#####################################################################################
		predicted.geometry = VectorValidation.__fixGeometries(predicted.geometry)
		validation.geometry = VectorValidation.__fixGeometries(validation.geometry)
		extents.geometry = VectorValidation.__fixGeometries(extents.geometry)
		if exclusionMask_fileName is not None:
			exclusionMask.geometry = VectorValidation.__fixGeometries(exclusionMask.geometry)

		#####################################################################################
		################ reset indices ##############
		#####################################################################################
		predicted = predicted.reset_index(drop=True)
		validation = validation.reset_index(drop=True)
		extents = extents.reset_index(drop=True)
		if exclusionMask_fileName is not None:
			exclusionMask = exclusionMask.reset_index(drop=True)

		#####################################################################################
		################ Remove empties #############
		#####################################################################################

		predicted = predicted.loc[~predicted.is_empty]
		validation = validation.loc[~validation.is_empty]
		extents = extents.loc[~extents.is_empty]
		if exclusionMask_fileName is not None:
			exclusionMask = exclusionMask.loc[~exclusionMask.is_empty]

		#####################################################################################
		################ reset indices ##############
		#####################################################################################
		predicted = predicted.reset_index(drop=True)
		validation = validation.reset_index(drop=True)
		extents = extents.reset_index(drop=True)
		if exclusionMask_fileName is not None:
			exclusionMask = exclusionMask.reset_index(drop=True)

		#####################################################################################
		#### segment into primary dataframes ####
		#####################################################################################
		if verbose:
			print("Primary overlays ...")

		# if verbose:
			# print("\tTP ...",end='\r')
		# TP = gpd.overlay(predicted,validation,how='intersection')

		# if verbose:
			# print("\t\tFP ...",end='\r')
		# FP = gpd.overlay(predicted,validation,how='difference')

		# if verbose:
			# print("\t\t\tFN ...",end='\r')
		# FN = gpd.overlay(validation,predicted,how='difference')

		# if verbose:
			# print("\t\t\t\tTN ...")

		# diffPred = gpd.overlay(extents,predicted,how='difference')


		with ThreadPoolExecutor(max_workers=4) as executor:

			arguments = {
							'TP' : {'df1' : predicted,'df2' : validation,'how':'intersection'},
							'FP' : {'df1' : predicted,'df2' : validation,'how':'difference'},
							'FN' : {'df1' : validation,'df2' : predicted,'how':'difference'},
							'diffPred' : {'df1' : extents,'df2' : predicted,'how':'difference'}
						}

			processes = {executor.submit(gpd.overlay,**argument) : name for name,argument in arguments.items()}

			for f in as_completed(processes):
				if verbose:
					print("\t{} completed".format(processes[f]))

				if processes[f] == 'TP':
					TP = f.result()

				if processes[f] == 'FP':
					FP = f.result()

				if processes[f] == 'FN':
					FN = f.result()

				if processes[f] == 'diffPred':
					diffPred = f.result()

					def calculateTN(diffPred,validation):

						diffPred = diffPred.explode() # explode
						diffPred.geometry = diffPred.geometry.apply(lambda x: VectorValidation.__roundGeometry(x,4)) # roundG
						diffPred.geometry = VectorValidation.__fixGeometries(diffPred.geometry) # fix
						diffPred = diffPred.reset_index(drop=True) # reset
						diffPred = diffPred.loc[~diffPred.is_empty] # remove null
						diffPred = diffPred.reset_index(drop=True) # reset

						TN = gpd.overlay(diffPred,validation,how='difference')

						return(TN)

					TN = executor.submit(calculateTN,*[diffPred,validation]).result()

		if verbose:
			print('\tTN completed')


		#####################################################################################
		######### extract areas ##########
		#####################################################################################

		if verbose:
			print("Extracting areas ...")
		TP_area = TP.geometry.area.sum() / (10**6)
		FN_area = FN.geometry.area.sum() / (10**6)
		FP_area = FP.geometry.area.sum() / (10**6)
		TN_area = TN.geometry.area.sum() / (10**6)

		#####################################################################################
		########### calculate metrics ##############
		#####################################################################################

		if verbose:
			print("Calculate metrics ...")

		total_area = TP_area + FN_area + FP_area + TN_area
		predPositive_area = TP_area + FP_area
		predNegative_area = TN_area + FN_area
		obsPositive_area = TP_area + FN_area
		obsNegative_area = TN_area + FP_area

		TP_perc = (TP_area / total_area) * 100
		FP_perc = (FP_area / total_area) * 100
		TN_perc = (TN_area / total_area) * 100
		FN_perc = (FN_area / total_area) * 100

		predPositive_perc = predPositive_area / total_area
		predNegative_perc = predNegative_area / total_area
		obsPositive_perc = obsPositive_area / total_area
		obsNegative_perc = obsNegative_area / total_area

		# over-prediction
		positiveDiff_area = predPositive_area - obsPositive_area
		positiveDiff_perc = predPositive_perc - obsPositive_perc

		# secondary metrics
		prevalance = (TP_area + FN_area) / total_area
		PPV = TP_area / predPositive_area
		NPV = TN_area / predNegative_area
		TPR = TP_area / obsPositive_area
		TNR = TN_area / obsNegative_area
		ACC = (TP_area + TN_area) / total_area
		F1_score = (2*TP_area) / (2*TP_area + FP_area + FN_area)
		Bal_ACC = np.mean([TPR,TNR])
		MCC = (TP_area*TN_area - FP_area*FN_area)/ np.sqrt((TP_area+FP_area)*(TP_area+FN_area)*(TN_area+FP_area)*(TN_area+FN_area))
		CSI = TP_area / (TP_area + FP_area + FN_area)

		stats = OrderedDict([	('TP_perc' , TP_perc),('FP_perc' , FP_perc),
					('TN_perc' , TN_perc),('FN_perc' , FN_perc),
					('TP_area' , TP_area),('FP_area' , FP_area),
					('TN_area' , TN_area),('FN_area' , FN_area),
					('total_area' , total_area),
					('prevalance' , prevalance),
					('predPositive_perc' , predPositive_perc),
					('predNegative_perc' , predNegative_perc),
					('obsPositive_perc' , obsPositive_perc),
					('obsNegative_perc' , obsNegative_perc),
					('predPositive_area' , predPositive_area),
					('predNegative_area' , predNegative_area),
					('obsPositive_area' , obsPositive_area),
					('obsNegative_area' , obsNegative_area),
					('positiveDiff_area' , positiveDiff_area),
					('positiveDiff_perc' , positiveDiff_perc),
					('PPV' , PPV),
					('NPV' , NPV),
					('TPR' , TPR),
					('TNR' , TNR),
					('ACC' , ACC),
					('F1_score' , F1_score),
					('Bal_ACC' , Bal_ACC),
					('MCC' , MCC),
					('CSI' , CSI)
				])


		#####################################################################################
		########### write stats to file ###########
		#####################################################################################
		if output_statistics_fileName is not None:

			fileOut = open(output_statistics_fileName,'w+')

			for key,value in stats.items():
				fileOut.write("{} = {:0.6f}\n".format(key,value))

			fileOut.close()


		#####################################################################################
		########## print stats ############
		#####################################################################################
		if verbose:
			for key,value in stats.items():
				print("{} = {:0.4f}".format(key,value))


		#####################################################################################
		##################################### write map #####################################
		#####################################################################################
		if output_map_fileName is not None:

			if verbose:
				print('Writing output maps ...')

			"""

			def dissolveConditions(conditionLayer,conditionString):

				# prep for dissolve
				conditionLayer = conditionLayer.explode() # explode
				conditionLayer.geometry = conditionLayer.geometry.apply(lambda x: VectorValidation.__roundGeometry(x,4)) # roundG
				conditionLayer.geometry = VectorValidation.__fixGeometries(conditionLayer.geometry) # fix
				conditionLayer = conditionLayer.reset_index(drop=True) # reset
				conditionLayer = conditionLayer.loc[~conditionLayer.is_empty] # remove null
				conditionLayer = conditionLayer.reset_index(drop=True) # reset

				conditionLayer = pd.DataFrame({'geometry':[conditionLayer.unary_union],'condition':conditionString})

				return(conditionLayer)

			with ThreadPoolExecutor(max_workers=4) as executor:

				arguments = {
							'TP' : {'conditionLayer' : TP , 'conditionString' : 'TP'},
							'FP' : {'conditionLayer' : FP , 'conditionString' : 'FP'},
							'FN' : {'conditionLayer' : FN , 'conditionString' : 'FN'},
							'TN' : {'conditionLayer' : TN , 'conditionString' : 'TN'}
					   	   }

				processes = {executor.submit(dissolveConditions,**argument) : name for name,argument in arguments.items()}

				for f in as_completed(processes):

					if verbose:
						print("\t{} completed".format(processes[f]))

					if processes[f] == 'TP':
						TP = f.result()

					if processes[f] == 'FP':
						FP = f.result()

					if processes[f] == 'FN':
						FN = f.result()

					if processes[f] == 'TN':
						TN = f.result()
			"""
			TP = TP.assign(condition='TP') ; FN = FN.assign(condition='FN') ; FP = FP.assign(condition='FP') ;TN = TN.assign(condition='TN')

			## concatanate
			try:
				differenceVectorLayer = pd.concat([TP,FN,FP,TN], ignore_index=True,sort=False)
			except TypeError: # backwards compatability for pandas (< 0.23.0)
				differenceVectorLayer = pd.concat([TP,FN,FP,TN], ignore_index=True)

			# save only condition and geometry columns
			differenceVectorLayer = differenceVectorLayer[['condition','geometry']]
			differenceVectorLayer = differenceVectorLayer.astype({'condition' : str})
			# differenceVectorLayer.to_csv('saving.csv',index=False)

			# convert to geoframes and format
			differenceVectorLayer = gpd.GeoDataFrame(differenceVectorLayer, crs=projection,geometry='geometry')
			# differenceVectorLayer = differenceVectorLayer.rename(columns={'0': 'geometry'}).set_geometry('geometry')

			# reexplode
			differenceVectorLayer = differenceVectorLayer.explode()
			differenceVectorLayer = differenceVectorLayer.reset_index(drop=True)
			differenceVectorLayer = differenceVectorLayer.loc[~differenceVectorLayer.is_empty]
			differenceVectorLayer = differenceVectorLayer.reset_index(drop=True)

			#get drivers
			driverDictionary = {'.gpkg' : 'GPKG','.geojson' : 'GeoJSON','.shp' : 'ESRI Shapefile'}
			driver = driverDictionary[splitext(output_map_fileName)[1]]

			# write to file
			differenceVectorLayer.to_file(output_map_fileName,schema={'geometry':'Polygon','properties':{'condition': 'str'}},driver=driver)


			return(stats,differenceVectorLayer)

		return(stats)

	@staticmethod
	def __simplifyGeoDataFrame(gdf,simplify_tolerance):

		gdf_simplified = gdf.simplify(simplify_tolerance)
		gdf_simplified = gdf_simplified.rename('geometry')
		gdf_simplified = gpd.GeoDataFrame(gdf_simplified)

		return(gdf_simplified)

	@staticmethod
	def __fixGeometries(geometrySeries):

		invalidGeometriesBoolean = ~geometrySeries.is_valid
		if invalidGeometriesBoolean.any():
			return(geometrySeries.buffer(0))
		else:
			return(geometrySeries)


	@staticmethod
	def __roundGeometry(geometry, precision=5):

		def around(coords, precision=5):
			result = []
			try:
				return round(coords, precision)
			except TypeError:
				for coord in coords:
					result.append(around(coord, precision))
			return result

		geojson = mapping(geometry)
		geojson['coordinates'] = around(geojson['coordinates'],precision)

		return shape(geojson)

	@staticmethod
	def __fishnet(geometry, threshold,verbose):
		bounds = geometry.total_bounds
		#bounds = [bounds['minx'].min(),bounds['miny'].min(),bounds['maxx'].max(),bounds['maxy'].max()]
		xmin = int(bounds[0] // threshold)
		xmax = int(bounds[2] // threshold)
		ymin = int(bounds[1] // threshold)
		ymax = int(bounds[3] // threshold)
		ncols = int(xmax - xmin + 1)
		nrows = int(ymax - ymin + 1)
		# print(ncols,nrows);exit()
		result = []
		for i in tqdm(range(xmin, xmax+1),disable=(not verbose)):
			for j in range(ymin, ymax+1):
				b = box(i*threshold, j*threshold, (i+1)*threshold, (j+1)*threshold)
				g = geometry.intersection(b)
				nonEmptyRows = ~g.is_empty
				nonEmptyGeometries = g.loc[nonEmptyRows]
				for ii in nonEmptyGeometries:
					result.append(ii)
		return result

	@staticmethod
	def __fishnetGeoDataFrame(gdf,threshold,verbose):

		gdfGeometries = VectorValidation.__fishnet(gdf.geometry,threshold,verbose)
		desiredCRS = gdf.crs
		gdf = gpd.GeoDataFrame({ 'geometry' : gdfGeometries }, crs = desiredCRS , geometry = 'geometry')
		# gdf = gpd.GeoDataFrame(gpd.GeoSeries(gdfGeometries,name='geometry'))
		# gdf.crs = {'init' : desiredCRS}
		# gdf.set_geometry = 'geometry'

		return(gdf)

	@staticmethod
	def __katana(geometry, threshold, count=0):
		"""Split a Polygon into two parts across it's shortest dimension"""
		bounds = geometry.bounds
		width = bounds[2] - bounds[0]
		height = bounds[3] - bounds[1]

		if max(width, height) <= threshold or count == 250:
			# either the polygon is smaller than the threshold, or the maximum
			# number of recursions has been reached
			return [geometry]
		if height >= width:
			# split left to right
			a = box(bounds[0], bounds[1], bounds[2], bounds[1]+height/2)
			b = box(bounds[0], bounds[1]+height/2, bounds[2], bounds[3])
		else:
			# split top to bottom
			a = box(bounds[0], bounds[1], bounds[0]+width/2, bounds[3])
			b = box(bounds[0]+width/2, bounds[1], bounds[2], bounds[3])
		result = []
		for d in (a, b,):
			c = geometry.intersection(d)
			if not isinstance(c, GeometryCollection):
				c = [c]
			for e in c:
				if isinstance(e, (Polygon, MultiPolygon)):
					result.extend(VectorValidation.__katana(e, threshold, count+1))
		if count > 0:
			return result
		# convert multipart into singlepart
		final_result = []
		for g in result:
			if isinstance(g, MultiPolygon):
				final_result.extend(g)
			else:
				final_result.append(g)
		return final_result

	@staticmethod
	def __katanaGeoDataFrame(gdf,threshold,verbose,name=None):

		gdf = gdf.explode()
		gdf_geom = gdf.geometry.unary_union
		split_gdf = VectorValidation.__katana(gdf_geom,threshold,count=0)

		if verbose & (name is not None):
			print("\tcompleted splitting {}".format(name))

		return(gpd.GeoDataFrame(gpd.GeoSeries(split_gdf,crs=gdf.crs,name='geometry')))


if __name__ == '__main__':

	# parse arguments
	parser = argparse.ArgumentParser(description='Provide three vector files to output binary contigency stats. Do not need to have the same spatial projections.')
	parser.add_argument('-p','--predicted', help='Predicted inundation vector filename', required=True)
	parser.add_argument('-v','--validation', help='Validation inundation vector filename', required=True)
	parser.add_argument('-a','--analysis-extents',help='Analysis extents vector filename',required=True)
	parser.add_argument('-e','--exclusion-mask',help='Set an exclusion mask to exclude from analysis inside analysis extents',required=False,default=None)
	parser.add_argument('-t','--threshold',help='Set threshold to split grid in meters',required=False,default=None,type=int)
	parser.add_argument('-l','--simplify-tolerance',help='Set tolerance to simplify all input vectors in meters. Set to 0 for no simplifying',required=False,default=10,type=int)
	parser.add_argument('-m','--map-output',help='Output map vector filename',required=False,default=None)
	parser.add_argument('-s','--stats-output',help='Output statistics csv filename',required=False,default=None)
	parser.add_argument('-q','--quiet',help='Quiet output',required=False,default=True)

	# extract to dictionary
	args = vars(parser.parse_args())

	# rename variable inputs
	predicted_fileName = args['predicted']
	validation_fileName = args['validation']
	analysisExtents_fileName = args['analysis_extents']
	split_threshold_meters = args['threshold']
	simplify_tolerance_meters = args['simplify_tolerance']
	exclusionMask_fileName = args['exclusion_mask']
	output_map_fileName = args['map_output']
	output_statistics_fileName = args['stats_output']
	verbose = args['quiet']

	# run function
	VectorValidation.binaryEvaluation(predicted_fileName=predicted_fileName,
									  validation_fileName=validation_fileName,
									  analysisExtents_fileName=analysisExtents_fileName,
									  exclusionMask_fileName=exclusionMask_fileName,
									  output_map_fileName=output_map_fileName,
									  output_statistics_fileName=output_statistics_fileName,
									  split_threshold_meters=split_threshold_meters,
									  simplify_tolerance_meters=simplify_tolerance_meters,
									  verbose=verbose)
