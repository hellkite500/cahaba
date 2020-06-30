#!/usr/bin/env python3



def compute_stats_from_contingency_table(true_negatives, false_negatives, false_positives, true_positives, cell_area):
    
    import numpy as np
    
    total_population = true_negatives + false_negatives + false_positives + true_positives
        
    # Basic stats.
    percent_correct = (true_positives + true_negatives) / total_population
    pod             = true_positives / (true_positives + false_negatives)
    far             = false_positives / (true_positives + false_positives)
    csi             = true_positives / (true_positives + false_positives + false_negatives)
    bias            = (true_positives + false_positives) / (true_positives + false_negatives)
    
    # Compute equitable threat score (ETS) / Gilbert Score. 
    a_ref = ((true_positives + false_positives)*(true_positives + false_negatives)) / total_population
    equitable_threat_score = (true_positives - a_ref) / (true_positives - a_ref + false_positives + false_negatives)

    total_population = true_positives + false_positives + true_negatives + false_negatives
    TP_perc = (true_positives / total_population) * 100
    FP_perc = (false_positives / total_population) * 100
    TN_perc = (true_negatives / total_population) * 100
    FN_perc = (false_negatives / total_population) * 100
        
    TP_area = true_positives * cell_area
    FP_area = false_positives * cell_area
    TN_area = true_negatives * cell_area
    FN_area = false_negatives * cell_area
    total_area = total_population * cell_area
    
    total_population = true_positives + false_positives + true_negatives + false_negatives
    predPositive = true_positives + false_positives
    predNegative = true_negatives + false_negatives
    obsPositive = true_positives + false_negatives
    obsNegative = true_negatives + false_positives
    
    predPositive_perc = predPositive / total_population
    predNegative_perc = predNegative / total_population
    obsPositive_perc = obsPositive / total_population
    obsNegative_perc = obsNegative / total_population
    
    predPositive_area = predPositive * cell_area
    predNegative_area = predNegative * cell_area
    obsPositive_area =  obsPositive * cell_area
    obsNegative_area =  obsNegative * cell_area
    
    positiveDiff_area = predPositive_area - obsPositive_area
    positiveDiff_perc = predPositive_perc - obsPositive_perc
    
    prevalence = (true_positives + false_negatives) / total_population
    PPV = true_positives / predPositive
    NPV = true_negatives / predNegative
    TPR = true_positives / obsPositive
    TNR = true_negatives / obsNegative
    ACC = (true_positives + true_negatives) / total_population
    Bal_ACC = np.mean([TPR,TNR])
    F1_score = (2*true_positives) / (2*true_positives + false_positives + false_negatives)
    MCC = (TP_area*TN_area - FP_area*FN_area)/ np.sqrt((TP_area+FP_area)*(TP_area+FN_area)*(TN_area+FP_area)*(TN_area+FN_area))

    stats_dictionary = {'percent_correct': percent_correct,
                        'pod': pod,
                        'far': far,
                        'csi': csi,
                        'bias': bias,
                        'equitable_threat_score': equitable_threat_score,
                        'TP_perc': TP_perc,
                        'FP_perc': FP_perc,
                        'TN_perc': TN_perc,
                        'FN_perc': FN_perc,
                        'total_area': total_area,
                        'prevalence': prevalence,
                        'predPositive_perc': predPositive_perc,
                        'predNegative_perc': predNegative_perc,
                        'obsPositive_perc': obsPositive_perc,
                        'obsNegative_perc': obsNegative_perc,
                        'predPositive_area': predPositive_area,
                        'predNegative_area': predNegative_area,
                        'obsPositive_area': obsPositive_area,
                        'obsNegative_area': obsNegative_area,
                        'positiveDiff_area': positiveDiff_area,
                        'positiveDiff_perc': positiveDiff_perc,
                        'PPV': PPV,
                        'NPV': NPV,
                        'TPR': TPR,
                        'TNR': TNR,
                        'ACC': ACC,
                        'F1_score': F1_score,
                        'Bal_ACC': Bal_ACC,
                        'MCC': MCC
                        }

    return stats_dictionary


def compare_two_rasters(benchmark_raster_path, predicted_raster_path, output_agreement_raster, pod_analysis_workspace, config):
    """
    Produces contingency table from 2 rasters and returns it. Also exports an agreement raster classified as:  TODO Change to...
        0: True Negatives
        1: False Negative
        2: False Positive
        3: True Positive
    
    """
    
    import rasterio
    import numpy as np
        
    print("Loading rasters...")
    benchmark_src = rasterio.open(benchmark_raster_path)
    benchmark_array = benchmark_src.read(1)
    predicted_src = rasterio.open(predicted_raster_path)
    predicted_array = predicted_src.read(1)
    
    # Ensure zeros and ones for binary comparison. Assume that positive values mean flooding and 0 or negative values mean dry. TODO. 

    print("Creating agreement raster...")
    agreement_array = np.add(benchmark_array, 2*predicted_array)
    with rasterio.Env():
        profile = benchmark_src.profile
        profile.update(nodata=None)
        with rasterio.open(output_agreement_raster, 'w', **profile) as dst:
            dst.write(agreement_array.astype(rasterio.uint8), 1)

    print("Getting pixel counts...")
    true_negatives = int((agreement_array == 0).sum())
    false_negatives = int((agreement_array == 1).sum())
    false_positives = int((agreement_array == 2).sum())
    true_positives = int((agreement_array == 3).sum())

    contingency_table_dictionary = { 'true_negatives': true_negatives,
                                     'false_negatives': false_negatives,
                                     'false_positives': false_positives,
                                     'true_positives': true_positives
                                    }                                       

    return contingency_table_dictionary
    