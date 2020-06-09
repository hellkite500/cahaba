'''----------------------------------------------------------------------------
 Tool Name:   GenerateNodeIDs
 Source Name: generatefromtonodeforlines.py modified from generate_node_ids.py
 Description: Generates or updates the FROM_NODE and TO_NODE fields
              for each line feature in the "Line" feature class.
              The function creates the fields if they do not already exist.
----------------------------------------------------------------------------'''
import sys
import os
import gc 
import datetime
import argparse

FN_FROMNODE = "From_Node"
FN_TONODE = "To_Node"

def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe())
    # Get Python syntax error
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

class GenerateFromToNodeforLines(object):
    '''Tool class for generating to and from node ids.'''
    def __init__(self):
        '''Define tool properties (tool name is the class name).'''
        self.label = 'Generate From/To Node for Lines'
        self.description = '''Generates the FROM_NODE and TO_NODE fields for each line feature.'''

    def setFromToNodeDict(self, streamnetwork, FN_HYDROID):
        sOK = 'OK' 
        try:
            input_lines = streamnetwork.copy()
            # Add fields if not they do not exist.
            if not FN_FROMNODE in input_lines.columns:
                input_lines[FN_FROMNODE] = ''
            
            if not FN_TONODE in input_lines.columns:
                input_lines[FN_TONODE] = ''
            
            # PU_Order = 'PU_Order'
            # # Create PU_Order field
            # if not PU_Order in input_lines.columns:
            #     input_lines[PU_Order] = ''
            
            input_lines_sort = input_lines.sort_values(by=[FN_HYDROID], ascending=True).copy()
            # input_lines_sortgeom = input_lines.sort_values(by=['geometry'], ascending=True).copy()
            
            xy_dict = {}
            bhasnullshape=False
            for rows in input_lines_sort[['geometry', FN_FROMNODE, FN_TONODE]].iterrows():             
                if rows[1][0]:
                    # From Node
                    firstx = round(rows[1][0].coords.xy[0][0], 7)
                    firsty = round(rows[1][0].coords.xy[1][0], 7)
                    from_key = '{},{}'.format(firstx, firsty)
                    if from_key in xy_dict:
#                        input_lines_sort[FN_FROMNODE][rows[0]] = xy_dict[from_key]
                        input_lines_sort.at[rows[0], FN_FROMNODE,] = xy_dict[from_key]
                    else:
                        xy_dict[from_key] = len(xy_dict) + 1
#                        input_lines_sort[FN_FROMNODE][rows[0]] = xy_dict[from_key]
                        input_lines_sort.at[rows[0], FN_FROMNODE,] = xy_dict[from_key]

                    # To Node
                    lastx = round(rows[1][0].coords.xy[0][-1], 7)
                    lasty = round(rows[1][0].coords.xy[1][-1], 7)
                    to_key = '{},{}'.format(lastx, lasty)
                    #if xy_dict.has_key(to_key):
                    if to_key in xy_dict:
#                        input_lines_sort[FN_TONODE][rows[0]] = xy_dict[to_key]
                        input_lines_sort.at[rows[0], FN_TONODE] = xy_dict[to_key]
                    else:
                        xy_dict[to_key] = len(xy_dict) + 1
#                        input_lines_sort[FN_TONODE][rows[0]] = xy_dict[to_key]
                        input_lines_sort.at[rows[0], FN_TONODE] = xy_dict[to_key]
                else:
                     bhasnullshape=True

            if bhasnullshape==True:
                print ("Some of the input features have a null shape.")
                print (FN_FROMNODE + " and " + FN_TONODE + " fields cannot be populated for those features.")
        except:
            print ("{}".format(trace()))
            sOK = 'NOTOK'
            gc.collect()  
        return (sOK, input_lines_sort)

if(__name__=='__main__'): 
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("-p", "--parameters", nargs='+', default=[], required=True,
                        help="list of parameters")
        args = ap.parse_args()
        streamnetwork = args.parameters[0]
        FN_HYDROID = args.parameters[1]
        
        oProcessor = GenerateFromToNodeforLines()
        tResults=None
        tResults = oProcessor.setFromToNodeDict(streamnetwork, FN_HYDROID)
        del oProcessor
    except:
        print (trace())
    finally:
        dt = datetime.datetime.now()
        print  ('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))
