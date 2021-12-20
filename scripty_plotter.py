"""
Wrapper around plotly for many parallel files.


This is intended as a module/library to make easy plots from data.
E.g. Plotly is great and allows shaded areas, toggleable lines, etc...
but the API is ridiculously complicated, and has unuseful defaults
-e.g. legend ordering.

Particularly data where there are many csv files, 
and they need preprocessing, before plotting.
Then further, if plots are not easy with excel
(e.g. shaded area plots)

Generally:
Make a plot holder object (a class)
Which comes with some sensible defaults, which can be overridden.
Adjust the parameters of the object (e.g. the title, or 
e.g. the regex that decides what files to use.)
Then call .plot on it, which will fill it with lines.
Do any further adjustment to the .fig object
Then .draw - to get it out as a html file etc.


Each file will be parsed, and used to make one or more lines on the end plot:
It will load the files straightforwardly into a pandas dataframe. (so columns are column titles)
Then a pre-processing function is called on each dataframe - the results of the preprocessing function are plonked into a dict of dataframes for plotting.
It can split the file (e.g. into UP and DOWN sections), with a suitable bit of text to append to file name (e.g. _u and _d)


The column name used for x and for y is passed through - the same for each file. The filename (post processing, and appending) is the legend label.

Limits are plotted too - passed as a dict of lines.
It can be easily done with a limits csv file too, though it won't be preprocessed - just x and y plotted with the same column titles.
(still quite up in the air - preprocessing and splitting.)
(Ideally it can be split too, to make multiple lines per CSV file.)


"""

import os
import sys
import re

import plotly
import pandas as pd


import csv


class plotHolder():
    
    def __init__(self):
        """Create a plotholder object - now setup the parameters!"""
        ##defaults for the various args
        #Generally where it is defined as None,
        # then a sensible default will be used when .plot is called.

        ##Directory to hunt for files
        self.cwd = "." 
        "Working directory for file loading"
            
        #Manual file list will override any logic following:
        self.fileList = None
        
        #For autogen a file list:
        #Permit only these matching files:
        #useful always to at least do csv files only.
        self.file_name_match_regex = re.compile(".*summary\.csv")

        #if defined, remove any matching files
        self.name_blacklist_regex =  None
        #e.g. re.compile(r"(?i)blue|thin") will remove (case insensitively) filenames with "blue" or "thin" in them
        
        #if defined, include only the matching files (note done last, after blacklist!)
        self.name_excl_whitelist_regex = None
        #e.g. bob.name_excl_whitelist_regex = re.compile(r"(?i)wigg") to permit "Wiggly" and "Wiggle" in filenmames only.


        ##i.e. keep only stuff left of the '__' or 'summary' if there is no '__'
        self.file_name_to_column_name_regex = \
        re.compile(".+?(?=__)|.+?(?=_summary)") 
        
        ##not used - a regex that only allows rows matching this to be parsed
        #self.row_match_regex = re.compile("^(Up|Down)$")

        #a function called per file with the pandas dataframe passed to it.
        #which it will modify and return
        self.custom_column_function = noop

        #a function called that returns a split dataset dict

        self.split_dataset_function = do_not_split

        #For use with split datasets - key is the same as split dataset dict key
        #e.g. {'_u':'triangle-right','_d':'triangle-left'}
        self.custom_markers_dict = None
        ##Marker size for custom markers
        self.marker_size = 5

        #A dict of limits - key is series title, data is a pair of arrays ([x points], [y points])
        #note the last one in the dict is plotted last - on top.
        self.limits_dict = None

        #the name of the column in pandas for these:
        self.x_col = "x"
        self.y_col = "y"

        self.x_err_plus = None
        self.x_err_minus = None

        self.y_err_plus = None
        self.y_err_minus = None

        self.shaded_y_error = False

        self.group_derivative_plots_together = False
        self.toggle_derivative_plots_together = False

        self.colourSequence = plotly.colors.qualitative.Plotly
        #default colours go: 
        #['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
        ##will ideally accept arbitrary inputs here - e.g. red, blue, turquoise.
        ##https://plotly.com/python-api-reference/generated/plotly.colors.html


        ##Will default down the line to be x_col and y_col if not defined later
        self.x_title = None
        self.y_title = None


        #use a log axis:
        self.logx = False
        self.logy =False

        self.title = None
        

        #self.fileList = listFiles(self.cwd)

    def plot(self):
        #Finish and build a graph as defined in the rest of the class.

        ## allow overriding the file list externally.
        if self.fileList == None:
            self.fileList = self.getFileList()

        #print(self.fileList)

        pd.options.plotting.backend = "plotly"
        self.fig = plotly.graph_objects.Figure()
        self.fig.update_layout(title=self.title)
        
        rgba = [hex_rgba(c, transparency=1.0) for c in self.colourSequence]
        colourCycle = ['rgba'+str(elem) for elem in rgba]

        line_color=next_in_looped_list(colourCycle)
        #print(self.colourSequence)
        #exit()
        


        print("Plotting: ", end = "")
        for f in self.fileList:
            fname = os.path.basename(f)
            colname = self.file_name_to_column_name_regex.search(fname).group(0)

            in_df = pd.read_csv(f)
            split_df = self.split_dataset_function(in_df)

            for append_name_string, df in split_df.items():
                line_name = colname+append_name_string
                try:
                    
                    df = self.custom_column_function(df)

                    # xvars = list(df.loc[:,self.x_col])
                    # yvars = list(df[self.y_col])
                    xvars = df[self.x_col]
                    yvars = df[self.y_col]
                    
                    ##Plot a plain line
                    self.fig.add_trace(plotly.graph_objects.Scatter( 
                        x=xvars, y=yvars,
                        name=line_name,
                        showlegend=True,
                        #legendgroup = colname, 
                        meta = colname,       
                        mode='lines+markers',
                       # marker = dict(symbol = 'cross')
                    ))
                    #plot y error bars
                    if self.y_err_plus != None and self.y_err_minus !=None:
                        #print("error barrrs")
                        self.fig.update_traces(selector=dict(name=line_name), 
                        error_y=dict(
                            type='data',
                            visible= not self.shaded_y_error,
                            symmetric=False,
                            array = df[self.y_err_plus],
                            arrayminus= df[self.y_err_minus]
                        ))

                    ##Plot X error bars
                    if self.x_err_plus != None and self.x_err_minus !=None:
                        #print("error barrrs")
                        self.fig.update_traces(selector=dict(name=line_name), 
                        error_x=dict(
                            type='data',
                            symmetric=False,
                            array = df[self.x_err_plus],
                            arrayminus= df[self.x_err_minus]
                        ))
                    
                    if self.custom_markers_dict:
                        markericon = self.custom_markers_dict.get(append_name_string, None)
                        if markericon != None:
                            self.fig.update_traces(selector=dict(name=line_name), 
                            marker_symbol = markericon,
                            marker= dict(size = self.marker_size)
                            
                        )


                    print(colname+append_name_string + ', ', end= "")
                

                except Exception as e:
                    print(f"Something went wrong when plotting {fname}")
                    print(f"=> Exception is {type(e)} , with {e.args}")
            #Update colours, and add to groups
            #(last, so the colour iterator doesn't waste itself on failed plots)
            self.fig.update_traces(selector=dict(meta= colname),
                line = dict(color=next(line_color)), 
            )


        print("Done.")
        
        ##for doing shaded error bars...it needs to plot a contour from the top y to the bottom y
        # 
        ##and they need to be roughly the same colour.
        ##so...can either do in above, or can take all the lines off, recording the colours,
        #and then reorder
        #Note the error bar data is now attached to each line object...
        if self.shaded_y_error and self.y_err_plus != None and self.y_err_minus !=None:
            for data in self.fig.data: ##for each trace in order.
                #print(data)
                if data['error_y']['array'] is None or data['error_y']['arrayminus'] is None:
                    continue ##skip this one, no error bar data.

                x = list(data['x'])
                y_upper = list(data['y'] + data['error_y']['array'])
                y_lower = list(data['y'] - data['error_y']['arrayminus'])
                
                color = data['line']['color']
                color = rgba_set_opacity(color,0.2)
                
                self.fig.add_trace(
                    plotly.graph_objects.Scatter(
                        x = x+x[::-1], ##goes from start to end to start - closed loop
                        y = y_upper+y_lower[::-1], #stitches the top bars all around to the bottom ones
                        fill = 'toself',##good for a closed shape... note it will 'cancel out' if a single trace covers same area twice
                        fillcolor = color, ##transparentish
                        mode = 'none', ##forces no lines..
                        name=data['name']+"_eband", ##
                        hoverinfo = "skip", ##prevent it being displayed
                        showlegend = True, ##appear in legend
                        meta = data['meta'] ##copy metadata for later grouping.
                    )
                )



        ##shuffle ebands to the bottom, so drawn first:
        self.fig.data = self.fig.data[::-1]##reversed order

        #Limit line plotting - so drawn on top last
        if self.limits_dict:
            print("Plotting Limits")
            for l_name, t in self.limits_dict.items():
                
                xvars,yvars = t
                #yvars = df[self.y_col]
                self.fig.add_trace(plotly.graph_objects.Scatter( 
                        x=xvars, y=yvars,
                        name=l_name,
                        showlegend=True,
                        #legendgroup = colname, 
                        meta = 'Limit_lines',  
                        #legendrank=0,     ##if not reversed places at start
                        mode='lines',
                        hoverinfo = "skip",
                        line=dict(
                        color= 'red',
                        width=3
                        )
                       # marker = dict(symbol = 'cross')
                    ))

        ##
        if self.group_derivative_plots_together:
            rank = 1100
            for data in self.fig.data[::-1]:
                data['legendgroup'] = data['meta']
                data['legendrank'] = rank ##ensures the order comes out OK.
                rank = rank+1
                    

        #fig.showlegend = True
        if self.x_title == None:
            self.x_title = self.x_col

        if self.y_title == None:
            self.y_title = self.y_col

        self.fig.update_xaxes(title_text=self.x_title)
        self.fig.update_yaxes(title_text=self.y_title)

        if self.logx:
            self.fig.update_xaxes(type="log")
        if self.logy:
            self.fig.update_yaxes(type="log")

        self.fig.update_layout(
            hoverlabel_namelength=-1, #-1 allows full name
        )

        if self.toggle_derivative_plots_together:
            self.fig.update_layout(legend_groupclick="togglegroup")
        else:
            self.fig.update_layout(legend_groupclick="toggleitem")

        ##legend groupings stop if reversed.
        if self.group_derivative_plots_together:
            #self.fig.update_layout(legend_traceorder="grouped+reversed")
            self.fig.update_layout(legend_traceorder="grouped") ##ranking applied above
        else:
            self.fig.update_layout(legend_traceorder="reversed") ##as ranking not applied, need to reverse
        #Now free to do any other modifications to self.fig



    def show(self):
        print("Opeing plot in browser")
        self.fig.show()



    def getFileList(self):
        #Using the directories and regexes, return a list of data files to plot.
        print(f"Generating file list for directory {self.cwd}")
 
        files = [os.path.join(self.cwd,f) for f in os.listdir(self.cwd)]
 
        files = [f for f in files if os.path.isfile(f)]
        print(f"There are {len(files)} files in the directory")

        files.sort(key=lambda x: os.path.getmtime(x)) ##Sort by time (oldest first)
        files = [f for f in files if self.file_name_match_regex.match(f)]
        print(f"There are {len(files)} files post file match filtering")


        if self.name_blacklist_regex != None:
            blacklist = []
            for f in files:
                fname= os.path.basename(f)
                if self.name_blacklist_regex.search(fname):
                    #print(f"Delisting {fname}")
                    blacklist.append(f)

            for b in blacklist:
                files.remove(b)

            print(f"There are {len(files)} files post blacklist filtering")

        if self.name_excl_whitelist_regex != None:
            whitelist = []
            for f in files:
                fname= os.path.basename(f)
                if self.name_excl_whitelist_regex.search(fname):
                    #print(f"Delisting {fname}")
                    whitelist.append(f)

            files = whitelist

            print(f"There are {len(files)} files post whitelist filtering")
        

        return files
    




def noop(dataframe):
    #print(type(dataframe))
    return dataframe.copy(deep=True)
    

def do_not_split(df):
    rd = dict()
    rd[''] = df ##so '' gets appended = nothings
    return rd

 # convert plotly hex colors to rgba to enable transparency adjustments
def hex_rgba(hex, transparency):
    col_hex = hex.lstrip('#')
    col_rgb = list(int(col_hex[i:i+2], 16) for i in (0, 2, 4))
    col_rgb.extend([transparency])
    areacol = tuple(col_rgb)
    return areacol

def rgba_set_opacity(rgba_string, opacity):
    #e.g 'rgba(99, 110, 250, 1.0)'
    vals = rgba_string.lstrip(r'rgba(').rstrip(r')').split(',')
    vals = [s.strip() for s in vals]
    vals[3] = str(opacity)
    ret_string = "rgba({},{},{},{})".format(*vals)
    #print(ret_string)
    return ret_string



# Make sure the colors run in cycles if there are more lines than colors
def next_in_looped_list(list1):
    while True:
        for element in list1:
            yield element

def hello():
    print("Hello world")

def listFiles(wd):
    #print(os.listdir(wd))
    return os.listdir(wd)

def getArgs():
    print(sys.argv)





#get list of current wd.
#todo-if fed a directory, use it.




#Overall summary - collate CSVs, and turns each one into a column in output.

#Deals with up/down style tests, where the output sh

#For each .csv file in the current working directory, sorted by creation date.
# LPCurrent,  file1,  file2,...
#   0.1  ,      0.111,  0.1200, 
#  1.1  ,       1.111,  1.1200, 
#...

#In memory structure is a list of dicts, each one corresponding to a data row, and the keys
#as column headings.

#Can support arbitrary functions from the row data to the output value.


    
#############Configuration######################
out_file_name = "200a_updown_collated.csv" #Could make it run off the current WD

#include only the files that match this regex:
#file_name_match_regex = re.compile(".*summary\.csv")

#typically strip some of file name to get a shorter column name:
#file_name_to_column_name_regex = re.compile(".+?(?=__)|(^.*)_summary") ##i.e. keep only stuff left of a __ or a summary if there is no __



#formula to return data - called once per row of data.
#Passed a dict (the labelled row from the csv file) (also includes '_filetitle')
#Returns a dict, which will be combined with the rest for that column.
    #Special key '_row_identifier' is a dict that gets matched with the rows returned by get_row_scaffold

##In this case goes straight to calculating the percentage error vs the reference
def dataExtract(in_dict):
    row_identifier = {'LP-Test Name':in_dict.get('LP-Test Name', 'ERROR'), 
    'LP-Current':float(in_dict.get('LP-Current', 'NA'))}

    ref_i = float(in_dict.get("REF-I", 'nan'))
    dut_i = float(in_dict.get("MEAN-Adc", 'nan'))
    
    if "REVERSEDI" in in_dict.get('_filetitle', 'ERROR'):
        ref_i = -ref_i

    return {'I_error': (dut_i/ref_i)-1, '_row_identifier':row_identifier}



#Function to get row scaffold, as a list of dicts (one dict per row)
#The rows will be matched against it for validity (to figure out which one to put each file's data in)
#Note formats should match with dataExtract!
def get_row_scaffold():

    currents_list = [0.1,0.5,1.0,3.0,10.0,30.0,50.0,75.0,100.0,150.0,180.0,200.0]
    return_list_o_dicts = list()

    for i in range(0,len(currents_list)):
        return_list_o_dicts.append({})
        return_list_o_dicts[-1].update({'LP-Test Name': 'Up'})
        return_list_o_dicts[-1].update({'LP-Current': currents_list[i]})

    for i in reversed(range(0,len(currents_list))):
        return_list_o_dicts.append({})
        return_list_o_dicts[-1].update({'LP-Current': currents_list[i]})
        return_list_o_dicts[-1].update({'LP-Test Name': 'Down'})

    return return_list_o_dicts


#formula that returns true if the row should be used:
#Can also probably make all pass if sufficient sorting above

def rowValidate(in_dict):
    
    return row_match_regex.match(in_dict.get("LP-Test Name","NA_ERROR"))




##################END CONFIGURATION####################



#Get files as a list



def filesToDict(files):

    list_of_row_dicts = get_row_scaffold()
    for f in files:

        with open(f, newline='') as csvfile:
            ##fieldnames are automatically taken from first row if not specified.
            dictreader = csv.DictReader(csvfile, delimiter = ',') 

            column_identifier = file_name_to_column_name_regex.search(f).group(0)

            
            for row in (r for r in dictreader if rowValidate(r)):
                row.update({"_filetitle": f})
                ##each row reduced to ONE value, which is put into the dict_of_all_data
                row_data = dataExtract(row)
                row_identifier = row_data.pop('_row_identifier')

                row_name, row_value = row_data.popitem() #typically the rest lost.
                row_name =  row_name +"__"+ column_identifier         

                for i in list_of_row_dicts: #not optimal but fast enough.
                    if row_identifier.items() <= i.items():
                        #if the identfier is a subset (matches) - take the first one.
                        i.update({row_name: row_value})
                        break
    
    return list_of_row_dicts

                    



#now have a list of dicts of form:
#[{'LP-Current': 0.1, 'LP-Test Name': 'Up', 'I_error__mod3-cal1-repeatnextday': -0.013679792998976037, 'I_error__mod3-cal1-unfolded': -0.006499262642861936, 'I_error__mod3_cal1_200a_120v_updown_26Oct21-1707': -0.005632016824321129, 'I_error__mod3_fullsweep26Oct21-1539': -0.09139055221864001}, {'LP-Current': 0.5, 'LP-Test Name': 'Up', 'I_error__mod3-cal1-repeatnextday': -0.002611698035358323, 'I_error__mod3-cal1-unfolded': -0.0010814689468119365, 'I_error__mod3_cal1_200a_120v_updown_26Oct21-1707': -0.00142351916905481, 'I_error__mod3_fullsweep26Oct21-1539': -0.0903928460638701}, {'LP-Curr

##Write out - one row per row label!
# with open(out_file_name, 'w', newline='') as out_csvfile:
#     column_headers = list(list_of_row_dicts[0].keys())
#     csvwriter = csv.DictWriter(out_csvfile, fieldnames=column_headers)
#     csvwriter.writeheader()

#     for dict in list_of_row_dicts:
#         csvwriter.writerow(dict)



def wittyPlot(fig, df, equation, permitted_ranges):
    '''
    This function draws lines on a plot given a dataframe
    plus some reasonably compact stuff on what to plot?

    so it needs to know what columns to plot, maths to do, etc.
    essentially symbolic?
    So doing it as a function is easier..

    Can pass strings as the names of what to plot...
    Is there a way to pass equationy type things?
    '''
    return


    #df = pd.DataFrame(dict(a=[1,3,2], b=[3,2,1]))
    #fig = df.plot(title="Pandas Backend Example", template="simple_white",
    #              labels=dict(index="REF-I", value="MEAN-Adc", variable="option"))
    #fig.update_yaxes(tickprefix="$")
    #fig.show()


    #fig = plotly.graph_objects.Figure(data=plotly.graph_objects.Line(list_of_row_dicts))
    #fig.write_html('first_figure.html', auto_open=True)


