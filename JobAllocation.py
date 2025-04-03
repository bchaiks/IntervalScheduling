'''
Refactoring the notebooks to be in a script for easier 
management

'''

import Scripts.Data as sd
import Scripts.Optimization as opt
import numpy as np
import time

sFile = f"schedule.csv"
rFile = f"machine_info.csv"


rs = sd.RawSchedule(sFile, rFile)

# process raw data into input format
data = sd.InputData()
data.FillRealJobInfo(rs)
data.FillAdjacencyInfo(rs)

data.FillStartAndEndInfo(rs)
data.FillDummyJobs()


# optimize initial schedule
m = opt.Solver(data)
m.OptimizeGaps = False
m.OptimizeSchedule()

'''
Need to refactor so that if this is infeasible, it returns
a message that the current schedule is not feasible as given. 
'''

m.GetInitialPlan()

displayInitialPlot = True 
if displayInitialPlot:
	m.Inputs.Plot(m.OptimizationAssignments, "test", save = True, fileName = 'GapsOptimized')
	

	
	
	
	