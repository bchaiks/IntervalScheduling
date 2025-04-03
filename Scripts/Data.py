'''
Functions for loading 
a schedule, and for making a copy with 
specific dummy values for different purposes 
(i.e. initial optimal schedule, schedule with 
additional/optimized min/max Jobs that do not 
violate the naive min-night-Job etc.)
'''

import pandas as pd
import os
import math
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

class RawSchedule:
	def __init__(self, scheduleFile, machineInfoFile):
		self.StartKey = "startOrdinal"
		self.FinishKey = "finishOrdinal"
		self.IsLockedKey = "IsLocked"
		self.AdjacencyGroupKey = "AdjacencyGroup"
		self.MachineKey = "Machine"
		self.LengthKey = "Length"
		self.MachineNumberKey = "MachineId"
		self.GroupNameKey = "JobId"
		self.Schedule = self.ReadFile(scheduleFile, True)
		self.MachineInfo = self.ReadFile(machineInfoFile, False)
	
	def ReadFile(self, filePath, reformat):
		df = pd.read_csv(filePath)
		if reformat:
			df = self.ReformatSchedule(df)	
		return(df)
	
	def ReformatSchedule(self, sched):
		sched["Start"] = pd.to_datetime(sched["JobStart"]).dt.date
		sched["Finish"] = pd.to_datetime(sched["JobFinish"]).dt.date
		sched = sched.drop(["JobStart","JobFinish"],axis=1)
		# convert the dates to ordinal values. These are convenient for operating on the intervals.
		sched[self.StartKey] = sched["Start"].apply(lambda x: x.toordinal())
		sched[self.FinishKey] = sched["Finish"].apply(lambda x: x.toordinal())
		# compute the length of the Jobs, needed for the sorting in the heuristic approaches.
		sched['Length'] = sched[self.FinishKey] - sched[self.StartKey]
		sched["DummyLength"] = np.zeros(len(sched))
		
		return(sched)


class InputData:
	def __init__(self, minJob = 5, maxDummy = 3):
		self.Machines = []
		
		self.NumberOfMachines = 0
		
		self.AdjacentMachines = []
		self.MachineAdjacencyLists = {}
		self.JobAdjacencyLists = {}
		
		self.NumberOfRealReservations = 0
		
		self.MaxDummyMultiple = maxDummy
		
		self.MinJob = minJob
		
		self.GroupDict = {}
		self.JobDict = {}
		self.StartDict = {}
		self.LengthDict = {}
		self.FixedMachines = {}
		
		self.DummyJobs = {}
		
		self.MinStart = -1
		self.MaxStart = -1
		self.MaxEnd = -1
		
		
		'''
		So actually, looks like this just needs to tell you when the next/previous arrival is.
		or like, how many days to consider are totally open before/after this schedule snippet! 
		what this really does is put a limit on how far the last dummy Jobs extend beyond the 
		end, which will affect feasibility when we limit the number of small gaps
		during the feasibility portion.
		'''
		self.ScheduleStart = -1
		self.ScheduleEnd = -1
		self.BoundSchedule = False
		
		self.TestMaxName = "test_max"
	


	
	
	def FillAdjacencyInfo(self, rawInput):
		sched = rawInput.Schedule
		MachineInfo = rawInput.MachineInfo
		
		adjGrpKey = rawInput.AdjacencyGroupKey
		MachineKey = rawInput.MachineKey
			
		adjacentJobDict = {}
		for i in range(len(sched)):
			if adjGrpKey not in sched or math.isnan(sched[adjGrpKey][i]):
				continue
			if sched[adjGrpKey][i] not in adjacentJobDict:
				adjacentJobDict[sched[adjGrpKey][i]] = []
			adjacentJobDict[sched[adjGrpKey][i]].append(i)
		
		self.JobAdjacencyLists = adjacentJobDict
		
		for i in range(len(MachineInfo)-1):
			for j in range(i+1,len(MachineInfo)):
				if MachineInfo[str(MachineInfo[MachineKey][j])][i] == 1:
					if MachineInfo[MachineKey][i] not in self.MachineAdjacencyLists:
						self.MachineAdjacencyLists[MachineInfo[MachineKey][i]] = []
						self.AdjacentMachines.append(MachineInfo[MachineKey][i])
				
					if MachineInfo[MachineKey][j] not in self.MachineAdjacencyLists:
						self.MachineAdjacencyLists[MachineInfo[MachineKey][j]] = []
						self.AdjacentMachines.append(MachineInfo[MachineKey][j])
		
					self.MachineAdjacencyLists[MachineInfo[MachineKey][i]].append(MachineInfo[MachineKey][j])
					self.MachineAdjacencyLists[MachineInfo[MachineKey][j]].append(MachineInfo[MachineKey][i])
		
		self.Machines = np.unique(np.array(MachineInfo[MachineKey]))
		self.NumberOfMachines = len(self.Machines)

	
	def FillStartAndEndInfo(self, rawInfo, endExtension = -1, startExtension = -1):	
	
		'''
		TODO -- need to think about how to add MinJob + 1 days on the end, and then 
		let the last set of dummy values go all the way out
		
		ACTUALLY let the limit be an input, and then it will go to 
		min(limit, maxEnd + minJob + 1)
		'''
		startDates = np.unique(np.array(rawInfo.Schedule[rawInfo.StartKey]))
		endDates = np.unique(np.array(rawInfo.Schedule[rawInfo.FinishKey]))
		self.MinStart = min(startDates)
		self.MaxStart = max(startDates)
		self.MaxEnd = max(endDates)
		self.ScheduleEnd = self.MaxEnd
		self.ScheduleStart = self.MinStart
		if endExtension > 0:
			# this extends the schedule so that the model does not consider short Jobs 
			# at the end as problematic
			self.ScheduleEnd += endExtension 
			self.BoundSchedule = True
		if startExtension > 0 :
			self.ScheduleStart -= startExtension 
		

	def FillRealJobInfo(self, rawInfo):
		sched = rawInfo.Schedule
		self.NumberOfRealReservations = len(sched)
		arr = rawInfo.StartKey
		dep = rawInfo.FinishKey
		for i in range(self.NumberOfRealReservations):
			self.GroupDict[i] = sched[rawInfo.GroupNameKey][i]
			self.JobDict[i] = [sched[arr][i],sched[dep][i]]
			self.StartDict[i] = sched[arr][i]
			self.LengthDict[i] = sched[rawInfo.LengthKey][i]
			if sched[rawInfo.IsLockedKey][i] == 1:
				self.FixedMachines[i] = int(sched[rawInfo.MachineNumberKey][i])
	
	
	
	def FillDummyJobs(self, minNightJobs ={}, absoluteMaxJobs={}):
		
		j = len(self.JobDict)
			
		# need to make sure that the dummy Jobs go right up to the end 
		# of the schedule! Otherwise the clique constraints may cause problems... 
		for days in range(1 ,int(self.MinJob * self.MaxDummyMultiple + 1)):
			self.DummyJobs[days] = []
			
			for i in range(self.MaxEnd - self.MinStart): 
				if self.CheckInFeasibility(days, i + self.MinStart, minNightJobs, absoluteMaxJobs):
					# do not add gaps that are less than the mns for this day
					# or greater than possible
					# 
					continue
					
				elif self.MinStart + i + days <= self.MaxEnd + 1:			
					# maybe add a few extra beyond the real end??
					# probably doesn't matter though...
					# then remember to just add clique sum to 1 constraints
					# up to the MaxEnd!!!! 
					self.GroupDict[j] = -1
					self.JobDict[j] = [self.MinStart + i, self.MinStart + i + days]
					self.StartDict[j] =  self.MinStart + i
					self.LengthDict[j] = days
					self.DummyJobs[days].append(j)
					j += 1
		
	
	def CheckInFeasibility(self, length, day, minJobs, maxNightJobs):
		# always leave the dummy Jobs at the ends and beginning for feasibility's sake
		# But do not need to add short dummies before/after the real bookings
		if day < self.MinStart and length < self.MinStart - day:
			return(False)
		if day + length > self.ScheduleEnd:
			return(False)
		if day >= self.MaxEnd - 1 and length < self.ScheduleEnd - day:
			# do not need to add short Jobs at the end of the schedule
			return(False)
			
		minJobInFeas = False
		if day in minJobs:
			if length < minJobs[day]:

				minJobInFeas = True
		
		maxJobInFeas = False
		if day in maxNightJobs:
			if length > maxNightJobs[day]:
				maxJobInFeas = True
				
		return(minJobInFeas or maxJobInFeas)
		
		
	
	def ClearDummyJobs(self):
	
		for l in self.DummyJobs:
			for d in self.DummyJobs[l]:
				del(self.GroupDict[d])
				del(self.JobDict[d])
				del(self.StartDict[d])
				del(self.LengthDict[d])
			
		self.DummyJobs = {}
			
	
	def Plot(self, assignments, title, test = (0, 0), fileName='', save = False, changeSize = False, display = True):
		fontSize = 6
		size = (8,6)
		if changeSize:
			fontSize = 4
			size = (12,12)
			
		fig, ax = plt.subplots(figsize = size)   
		ax.set_ylim(1,self.NumberOfMachines + 1)
		ax.set_xlim(-1, self.ScheduleEnd-self.ScheduleStart + 1)
		ax.set_axisbelow(True)
		MachineMap = {}
		maxY = 0
		rmSigns = {}
		for i in range(self.NumberOfMachines):
			MachineMap[self.Machines[i]] = i + 1
			rmSigns[self.Machines[i]] = 1.0
			maxY =i+2
	
		tcks = np.arange(self.ScheduleStart, self.ScheduleEnd + 1)
		tcks = [t - self.ScheduleStart for t in tcks]
		rmtcks = np.arange(self.NumberOfMachines + 1)
		
		#plt.text(0.5,1,"Start", fontsize = fontSize)
		#plt.text(self.ScheduleEnd - self.ScheduleStart - 0.5,1,"end", fontsize = fontSize)	
		if self.BoundSchedule:
			ax.add_patch(Rectangle((0,0), width = 0.5, height=self.NumberOfMachines+1, alpha=0.3,
									   edgecolor = 'black', facecolor = 'black'))
			ax.add_patch(Rectangle((self.ScheduleEnd - self.ScheduleStart + 0.5,0), width = 0.5, height=self.NumberOfMachines+1, alpha=0.3,
									   edgecolor = 'black', facecolor = 'black'))
		
		
		for i in assignments:
			rm = MachineMap[assignments[i]]
			JobLength = test[1] 
			start = test[0]
			if i in self.JobDict:
				JobLength = self.JobDict[i][1] - self.JobDict[i][0]
				start = self.JobDict[i][0]
			
			color = 'gray'
			if i in self.FixedMachines:
				color = 'red'
			for s in self.JobAdjacencyLists:
				if i in self.JobAdjacencyLists[s]:
					color = 'blue'
					
			grpName = ""
			if i in self.GroupDict:
				if self.GroupDict[i] == -1:
					color = 'green'
					grpName = "-1"
				else:
					grpName = f"{self.GroupDict[i]}"
			else: 
				grpName = self.TestMaxName
				color = 'yellow'
			# want to change the color of the min Job... 
			# and max Job, I guess... 
		
			ax.add_patch(Rectangle((start - self.ScheduleStart + 0.5,rm-0.4), width = JobLength, height=.8, alpha=0.5,
								   edgecolor = 'black', facecolor = color))
			x = start - self.ScheduleStart + JobLength/2.0 
			y = rm  
			rmSigns[assignments[i]] = rmSigns[assignments[i]]  * -1
			plt.text(x,y,grpName, fontsize = fontSize)
		
		plt.grid()
		labels = ['']
		for r in self.Machines:
			labels.append(str(r))
		plt.xticks(ticks = tcks, labels = tcks, rotation='vertical', fontsize = 6)
		plt.yticks(ticks = rmtcks,labels = labels, fontsize = 6)
	
		plt.xlabel("Period")
		plt.ylabel("Machine ID")
		plt.title(title)
		if save:
			plt.savefig(fileName,dpi = 200)
		if display:
			plt.show()
		plt.close()

