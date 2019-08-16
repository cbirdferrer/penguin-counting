##---------------------------------------------------------------------------------------------
##PenguinPopulationCounts.py tool
##
##Description: In this tool the user identifies colonies that were falsey identified by the NIR tool and
##				, if the thermal image covers parts of the penguin habitat not covered by the NIR image the user can
##				draw polygons to include those colonies in the analysis as well. This tool creates a final CSV with the
##				population counts, colonies areas, denseties and colony ID numbers.
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
scratchWS = os.path.join(rootWS,"scratch") #goes to the scratch folder
resultWS = os.path.join(rootWS,"results") #goes to the results folder where the density data .csv will go
print (scratchWS)
mxd = arcpy.mapping.MapDocument("CURRENT")
mxd.relativePaths = True

#Set environment variables
arcpy.env.workspace = dataWS
arcpy.env.scratchWorkspace = scratchWS
arcpy.env.overwriteOutput = True

#User Inputs
#Set input dataset (thermal image raster)
inputFile = arcpy.GetParameterAsText(0)

#get if points are selecting true colonies or false colonies
CorORIncor = arcpy.GetParameterAsText(1)

#get colony points (user clicks to create)
DefCol = arcpy.GetParameterAsText(2)

#get colonies that are missing from multispec because of different coverage or other
ThermCol = arcpy.GetParameterAsText(3)

#Input Error Messages
desc = arcpy.Describe(inputFile)
datatype = desc.dataType
if datatype != "RasterDataset":
	arcpy.AddError("Data type:" + datatype + " is not correct for this tool. Please input a raster layer.")

#Process: Make Feature Layer (for select layer by location input)
potentialcol = scratchWS+"\\potential_colonies.shp"
maybecollyr = scratchWS+"\\guano_maybe_col.lyr"
arcpy.MakeFeatureLayer_management(potentialcol, maybecollyr)

#Process: Select Layer By Location: get colonies through either select or inverting this tool based on first user input
if CorORIncor == "CORRECT":
	arcpy.SelectLayerByLocation_management(maybecollyr, "INTERSECT", DefCol, "","NEW_SELECTION")
if CorORIncor == "INCORRECT":
	arcpy.SelectLayerByLocation_management(maybecollyr, "INTERSECT", DefCol, "","NEW_SELECTION","INVERT")

#Process: Copy Features
nircolonies = scratchWS+"\\nir_colonies.shp"
arcpy.CopyFeatures_management(maybecollyr, nircolonies,"","0","0","0")

#combine the selected colonies and the drawn missing colonies
#Process: Union (join the colony layer w/ the thermal colonies)
allCol = scratchWS+"\\col_buff_mask_temp.shp"
arcpy.Union_analysis([nircolonies, ThermCol], allCol, "ALL", "","GAPS")

#Make the Buffered Mask
#Process: Buffer Penguin Colonies
BuffMask = scratchWS+"\\nircolony_buff.shp"
arcpy.Buffer_analysis(allCol, BuffMask, "0.5 Meters", "FULL", "ROUND", "NONE", "", "PLANAR")
#Process: Calculate Field for DISS field (so can dissolve the thermal and NIR colonies)
arcpy.CalculateField_management(BuffMask,"DISS","1","VB","")
#Process: Dissolve
ColBuffMask = scratchWS+"\\col_buff_mask.shp"
arcpy.Dissolve_management(BuffMask, ColBuffMask, "DISS","","SINGLE_PART","")
#Process: Add Geometry Attributes (needed for density calculations at the end)
arcpy.AddGeometryAttributes_management(ColBuffMask,"AREA","","SQUARE_METERS","")

#Make the Unbuffered Mask
#Process: Calculate Field for DISS field (so can dissolve the thermal and NIR colonies)
arcpy.CalculateField_management(allCol,"DISS","1","VB","")
#Process: Dissolve
ColMask = scratchWS+"\\col_mask.shp"
arcpy.Dissolve_management(allCol, ColMask, "DISS","","SINGLE_PART","")
#Process: Add Geometry Attributes (needed for density calculations at the end)
arcpy.AddGeometryAttributes_management(ColMask,"AREA","","SQUARE_METERS","")

#Process: Extract by Mask (extract colonies from thermal raster)
therm_col = scratchWS+"\\therm_colonies.img"
arcpy.gp.ExtractByMask_sa(inputFile, ColBuffMask, therm_col)

#Process: Filter (high pass)
highfilt = scratchWS+"\\highpass.img"
arcpy.gp.Filter_sa(therm_col, highfilt, "HIGH", "DATA")

#Process: Display high pass filter output
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
#create a temporary raster layer and add to map
tempLyr = arcpy.MakeRasterLayer_management(highfilt, 'tempRas', "","","")
layer = tempLyr.getOutput(0)
arcpy.mapping.AddLayer(df, layer, "TOP")
arcpy.RefreshActiveView()
arcpy.RefreshTOC()
del tempLyr, mxd, df

#check in the spatial extention
arcpy.CheckInExtension("Spatial")
