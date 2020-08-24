#---------------------------------------------------------------------------------------------
##FinalCounting_Step3.py tool
##
##Description: This tool uses selects penguins based on the output of the highpass filter
##				and then creates polygons of the number of penguins. It then creates a table
##				with the number of penguins in each colony and the density of penguins per sq. make
##				per colony
##
##Created: August 2018 (combination of December 2017 and March 2018)
##Author: Clara Bird - cnb21@duke.edu
##--------------------------------------------------------------------------------------------

#Import modules
import arcpy, os, sys
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
import pandas as pd

#Set realtive paths
scriptPath = sys.argv[0]
scriptWS = os.path.dirname(scriptPath) #gives the script folder
rootWS = os.path.dirname(scriptWS) #go up one folder to get to the project folder
dataWS = os.path.join(rootWS,"data") #go down into the data folder
scratchWS = os.path.join(rootWS,"docs\\scratch_torg") #goes to the scratch folder
resultWS = os.path.join(rootWS,"results") #goes to the results folder where the density data .csv will go
print (scratchWS)
mxd = arcpy.mapping.MapDocument("CURRENT")
mxd.relativePaths = True

#Set environment variables
arcpy.env.workspace = dataWS
arcpy.env.scratchWorkspace = scratchWS
arcpy.env.overwriteOutput = True

#User Inputs
#enter highpass filter threshold value
HighPass = arcpy.GetParameterAsText(0)
#get highpass threshold value as points to be averaged
hppoints = arcpy.GetParameterAsText(1)

#input identifying name to be used for output csv
id_name = arcpy.GetParameterAsText(2)

#path to highpass filter raster from step 2 tool
highfilt = scratchWS + "\\highpass.img"


#if statement saying to use the string threshold unless it wasn't provided
if HighPass != 'default':
	mean = HighPass
elif HighPass == 'default':
	#Process: Extract Multi Values to Points
	HP = scratchWS + "\\HP.shp"
	ExtractValuesToPoints(hppoints,highfilt,HP, "NONE","VALUE_ONLY")

	#Process: Summary Statistics
	arcpy.Statistics_analysis(HP, scratchWS +"\\hpvalues_mean.dbf", "RASTERVALU MEAN", "")

	#Create cursor to extract mean value from table
	cursor = arcpy.da.SearchCursor(scratchWS+"\\hpvalues_mean.dbf",['MEAN_RASTE'])
	for row in cursor:
		mean = row
	del cursor
	mean = str(mean)
	mean = mean.translate(None,"(),")
	arcpy.AddMessage("The mean highpass value is {0}.".format(mean))

#Process: resample
out_resample = scratchWS + "\\highfilt_resample_BL.img"
arcpy.Resample_management(highfilt, out_resample, "0.08", "BILINEAR")

#Process Con
therm_col = scratchWS + "\\therm_colonies.img"
out = scratchWS+"\\confilt.img"
SQL = "Value > {0}".format(HighPass)
arcpy.gp.Con_sa(out_resample, therm_col, out, "", SQL)

#Extract by unbuffered Mask
ColMask = scratchWS+"\\col_mask.shp"
outCon = scratchWS+"\\conmask.img"
arcpy.gp.ExtractByMask_sa(out, ColMask, outCon)

#Process Raster Calc *10
input = Raster(outCon)
outInt = input*10
#Process Raster int
output = scratchWS + "\\thermInt.img"
outInt = Int(outInt)
outInt.save(output)

#Process Raster to Polygon
outP = scratchWS + "\\therm_poly_all.shp" ##this is the actual output for the final tool
arcpy.RasterToPolygon_conversion(outInt,outP,"NO_SIMPLIFY","Value")
outPoly = scratchWS + "\\therm_poly.shp"
arcpy.Select_analysis(outP, outPoly, "gridcode > 0")

#Process: Add thermal value Field
arcpy.AddField_management(outPoly,"TEMP","DOUBLE")
#Process: Calculate values for thermal field
arcpy.CalculateField_management(outPoly,"TEMP","[gridcode] /10","VB","")

#Process: Add Field with value for dissolving
arcpy.AddField_management(outPoly,"DISS","DOUBLE")
#Process: Calculate Field for DISS field
arcpy.CalculateField_management(outPoly,"DISS","1","VB","")

#Process: Dissolve
penguins = scratchWS+"\\therm_poly_diss.shp"
arcpy.Dissolve_management(outPoly, penguins, "DISS", "", "SINGLE_PART","")
#Process: Add Geometry Attributes to dissolved polygons
arcpy.AddGeometryAttributes_management(penguins, "AREA","","SQUARE_METERS","")

#Save final polygons for colonies and penguins in results folder
#Colonies - Process: copy features into result folder
finalCol = resultWS+"\\colony_outlines_{0}.shp".format(id_name)
arcpy.CopyFeatures_management(ColMask, finalCol,"","0","0","0")
#Penguins - Process: copy features into result folder
finalPeng = resultWS+"\\penguins_{0}.shp".format(id_name)
arcpy.CopyFeatures_management(penguins, finalPeng, "","0","0","0")

#Display final colony outlines and penguin polygons
##COLONY OUTLINE
#Process: make layer
outLayer = scratchWS+"\\pengcolonies.lyr"
arcpy.MakeFeatureLayer_management(ColMask, outLayer)
#Process Apply Symbology
symbology = dataWS+"\\layers\\FinalColony.lyr"
arcpy.ApplySymbologyFromLayer_management(outLayer,symbology)

##PENGUIN POLYGONS
#Process: make layer
outPeng = scratchWS+"\\penguin.lyr"
arcpy.MakeFeatureLayer_management(penguins, outPeng)
#Process: Apply Symbology
symbol = dataWS+"\\layers\\penguins.lyr"
arcpy.ApplySymbologyFromLayer_management(outPeng, symbol)

#Process: Display Potential Penguin Colony Polygons
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
#add the final colony layer
addLayer = arcpy.mapping.Layer(outLayer)
if addLayer.supports("LABELCLASSES"):
    for lblclass in addLayer.labelClasses:
		lblclass.expression = "( [FID] )"
		lblclass.showClassLabels = True
addLayer.showLabels = True
arcpy.mapping.AddLayer(df, addLayer,"TOP")
#add the penguin polygon layer
addLayer = arcpy.mapping.Layer(outPeng)
arcpy.mapping.AddLayer(df, addLayer, "TOP")
arcpy.RefreshActiveView()
arcpy.RefreshTOC()

#This is all to get the population health metric table
#Process: Copy Features
density = scratchWS+"\\peng_col_dense.shp"
arcpy.CopyFeatures_management(ColMask, density, "", "", "", "")
#Process: Add Field (for keeping track of ID)
arcpy.AddField_management(density, "COLNUM","DOUBLE")
#Process: Calculate Field
arcpy.CalculateField_management(density,"COLNUM", "[FID]", "VB", "")
#Process:Make FeatureLayer
dense = scratchWS+"\\penguincolonydensity.lyr"
arcpy.MakeFeatureLayer_management(density, dense)

#Process: Spatial Join
outJoin = scratchWS+"\\join.shp"
arcpy.SpatialJoin_analysis(dense, penguins, outJoin, "JOIN_ONE_TO_MANY", "KEEP_ALL", "", "INTERSECT", "", "")

#Process arcpy to NumPy array
arr = arcpy.da.TableToNumPyArray(outJoin, ('COLNUM', 'POLY_AREA', 'POLY_ARE_1'))

#Make pandas dataframe from array
df_join = pd.DataFrame(arr)

#read in csv of join table
#df_join = pd.read_csv(wd+"\\avian_join1.csv",sep=",")
#loop through each penguin polygon and if area is greater than 3 pixels make the count more than 1 penguin
pengcountlist = []
for i in df_join['POLY_ARE_1']:
    if i > 0.069315:
        x = i/0.069315
        #print (x)
        if 1 < x < 2:
            x = 2
        elif x >= 2:
            x = x
        x = int(x)
        pengcountlist += [x]
    elif i <= 0.069315:
        x = 1
        pengcountlist += [x]
df_join['PENG_COUNT'] = pengcountlist

#calculate the number of penguins in each colony
df_grouped = df_join.groupby('COLNUM')['PENG_COUNT'].sum().reset_index()
df_area = df_join.groupby('COLNUM')['POLY_AREA'].mean().reset_index()
#clean up the csv for output
df_grouped['COL_AREA'] = df_area['POLY_AREA']
df_grouped['DENSITY'] = df_grouped['PENG_COUNT']/df_grouped['COL_AREA']
df_grouped.columns = ['COLONY_ID', 'PENG_COUNT', 'GUANO_sq_m', 'DENSITY']
df_grouped.to_csv(resultWS+"\\Colony_Penguin_Density_{0}.csv".format(id_name), sep = ',')

#remove the potential colonies and high pass layers
potcollyr = arcpy.mapping.Layer(scratchWS+"\\potential_colonies.lyr")
hplyr = arcpy.mapping.Layer("tempRas")
arcpy.mapping.RemoveLayer(df,potcollyr)
arcpy.mapping.RemoveLayer(df, hplyr)
arcpy.RefreshActiveView()
arcpy.RefreshTOC()
del addLayer, mxd, df

#check in the spatial extention
arcpy.CheckInExtension("Spatial")
