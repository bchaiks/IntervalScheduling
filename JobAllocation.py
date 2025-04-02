'''
Refactoring the notebooks to be in a script for easier 
management

'''

import Scripts.Data as sd
import Scripts.Optimization as opt
import numpy as np
import time
import json
import sys

sFile = f"schedule.csv"
rFile = f"machine_info.csv"


'''
NOTE: refactor this to just use python json library
'''
rs = sd.RawSchedule(sFile, rFile)

# process raw data into input format
data = sd.InputData()
data.FillRealStayInfo(rs)
data.FillAdjacencyInfo(rs)

data.FillStartAndEndInfo(rs)
data.FillDummyStays()


# optimize initial schedule
m = opt.Solver(data)
m.OptimizeGaps = True
m.OptimizeSchedule()

'''
Need to refactor so that if this is infeasible, it returns
a message that the current schedule is not feasible as given. 

Probably would be nice to know if it's because 
of adjacent rooms, or locked rooms, or something... 
'''

m.GetInitialPlan()

displayInitialPlot = True 
if displayInitialPlot:
	m.Inputs.Plot(m.OptimizationAssignments, "test", save = True, fileName = 'GapsOptimized')
	

	
	
	
	