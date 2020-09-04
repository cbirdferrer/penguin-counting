##---------------------------------------------------------------------------------------------
##multispec_colonies_step1.py tool
##this tool was built for senior thesis
##
##Description: this tool identifies potential penguin colonies using NIR or NDVI imagery which shows
##				the penguin guano. The user inputs the image and selects several pixels that
##				they can see are guano, these values are used to determine guano NIR threshold
##				value. This tool is meant as part 1, in the next tool the user will use the
##				output of this tool and thermal imagery to count penguin populations.
##
##Created: March 2018
##Author: Clara Bird - cnb21@duke.edu
##--------------------------------------------------------------------------------------------

#Import modules
import arcpy, os, sys
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
import arcpy.mapping

#Set realtive paths
scriptPath = sys.argv[0]
scriptWS = os.path.dirname(scriptPath) #gives the script folder
rootWS = os.path.dirname(scriptWS) #go up one folder to get to the project folder
dataWS = os.path.join(rootWS,"data") #go down into the data folder
scratchWS = os.path.join(rootWS,"scratch") #goes to the scratch folder
print scratchWS
mxd = arcpy.mapping.MapDocument("CURRENT")
mxd.relativePaths = True

#Set environment variables
arcpy.env.workspace = dataWS
arcpy.env.scratchWorkspace = scratchWS
arcpy.env.overwriteOutput = True

#Set input dataset (NIR raster)
inputFile = arcpy.GetParameterAsText(0)

##these next two inputs are both for thresholding the guano
##you can either input a value yourself or click points and the average will be calculated
#user inputs threshold as a string
guanothresh = arcpy.GetParameterAsText(1)
#get guano value inputs as points
guanovalues = arcpy.GetParameterAsText(2)

#Input Error Messages
desc = arcpy.Describe(inputFile)
datatype = desc.dataType
if datatype != "RasterDataset":
	arcpy.AddError("Data type:" + datatype + " is not correct for this tool. Please input a raster layer.")

#if statement saying to use the string threshold unless it wasn't provided
if guanothresh != "default":
	mean = guanothresh
elif guanothresh == "default":
	#Process: Extract Multi Values to Points
	Guano = scratchWS + "\\Guano.shp"
	ExtractValuesToPoints(guanovalues,inputFile,Guano, "NONE","VALUE_ONLY")

	#Process: Summary Statistics
	arcpy.Statistics_analysis(Guano, scratchWS +"\\guanovalues_mean.dbf", "RASTERVALU MEAN", "")

	#Create cursor to extract mean value from table
	cursor = arcpy.da.SearchCursor(scratchWS+"\\guanovalues_mean.dbf",['MEAN_RASTE'])
	for row in cursor:
		mean = row
	del cursor
	mean = str(mean)
	mean = mean.translate(None,"(),")
	arcpy.AddMessage("The mean guano spectral value is {0}.".format(mean))

#Process Con
SQL_expression = "Value > {0}".format(mean)
outCon = scratchWS+"\\guanocon1.img"
arcpy.gp.Con_sa(inputFile,inputFile,outCon,"",SQL_expression)

#Process Raster Calc *10
input = Raster(outCon)
outInt = input*10
#Process Raster int
output = scratchWS + "\\guanoInt.img"
outInt = Int(outInt)
outInt.save(output)

#Process Raster to Polygon
outP = scratchWS + "\\guano_poly_all.shp"
arcpy.RasterToPolygon_conversion(outInt,outP,"NO_SIMPLIFY","Value")
outPoly = scratchWS + "\\guano_poly.shp"
arcpy.Select_analysis(outP, outPoly, "gridcode > 0")

#Process: Add NIR value Field
arcpy.AddField_management(outPoly,"NIR","DOUBLE")
#Process: Calculate values for NIR field
arcpy.CalculateField_management(outPoly,"NIR","[gridcode] /10","VB","")

#Process: Add Field with value for dissolving
arcpy.AddField_management(outPoly,"DISS","DOUBLE")
#Process: Calculate Field for DISS field
arcpy.CalculateField_management(outPoly,"DISS","1","VB","")

#Process: Dissolve
outDiss = scratchWS+"\\guano_poly_diss.shp"
arcpy.Dissolve_management(outPoly, outDiss, "DISS", "", "SINGLE_PART","")
#Process: Add Geometry Attributes to dissolved polygons
arcpy.AddGeometryAttributes_management(outDiss, "AREA","","SQUARE_METERS","")

#Process: Select by area
outSel = scratchWS+"\\guano_poly_diss_sel.shp"
arcpy.Select_analysis(outDiss, outSel,"\"POLY_AREA\">0.3")
#Process: Buffer
outBuff = scratchWS+"\\guano_poly_diss_sel_buff.shp"
arcpy.Buffer_analysis(outSel, outBuff, "0.6 meters", "FULL","ROUND","NONE","","PLANAR")
#Process: Dissolve
guanoMaybeCol = scratchWS+ "\\potential_colonies.shp"
arcpy.Dissolve_management(outBuff,guanoMaybeCol,"DISS","","SINGLE_PART","")

#Process: make layer
outLayer = scratchWS+"\\potential_colonies.lyr"
arcpy.MakeFeatureLayer_management(guanoMaybeCol, outLayer)
#Process Apply Symbology
symbology = dataWS+"\\layers\\Colonies.lyr"
arcpy.ApplySymbologyFromLayer_management(outLayer,symbology)

#Process: Display Potential Penguin Colony Polygons
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
addLayer = arcpy.mapping.Layer(outLayer)
arcpy.mapping.AddLayer(df, addLayer,"TOP")
arcpy.RefreshActiveView()
arcpy.RefreshTOC()
del addLayer, mxd, df

#check in spatial extenstion
arcpy.CheckInExtension("Spatial")
