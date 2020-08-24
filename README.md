# penguin-counting
Repository for the software supplementary material of *A semi-automated method for estimating Adelie penguin colony abundance from a fusion of multispectral and thermal imagery collected with Unoccupied Aircraft Systems*

This repository contains the code, file structure, and toolbox set up to be imported into ArcGIS. This toolset isolates colonies from multispectral imagery, uses the outlines to clip the colonies from thermal imagery, and then counts the individual penguins within the thermal imagery.

The required file structure for the ArcGIS toolbox is:
```
folder
  \data
  \scratch
  \results
  \scripts
    \Step1
    \Step2
    \Step3
```

This toolset was developed using **ArcGIS Desktop 10.5.1**

Instructions are provided as GIS metadata for each tool. The metadata files have also been downloaded as pdfs, they can be found in the [guide docs](https://github.com/cbirdferrer/penguin-counting/tree/master/guide%20docs) folder.
