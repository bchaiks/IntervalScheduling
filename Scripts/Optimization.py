'''
build and solve optimization model

have to return the model, hopefully that brings with it all the 
solution info etc... 

actually, maybe make it a class. 
'''

import numpy as np
import math
import csv
from pyscipopt import Model, quicksum
import time


class Solution:
	def __init__(self):
		self.AssignmentValues = {}
		self.DummyIncentiveValues = {}

		

class Solver:
	def __init__(self, inputs):
		self.Solutions = []
		
		self.Inputs = inputs
		self.Time = 0.0
		self.MaxStayTime = 0.0
		
		# Cliques are stays that are all there on a given day, 
		# one list for each day. 
		self.Cliques = []
		
		self.Model = Model()
		
		self.ObjectiveCoefficients = {}
		self.AssignmentVars = {}
		
		 # these are for finding small/large gaps, don't always need
		self.DummyAssignmentVars = {}
		self.DummyStays = []
		
		# list of adjacent reservations:
		self.AdjacentReservations = []
		
		self.Succeeded = False
		self.ProvedInfeasible = False
		self.OptimizationAssignments = {}
		self.DummyOptimizedAssignments = {}# {(day,length): {}}
		
		
		self.MaxStayDesiredAssignments = {}# {(day,length): {}}
		self.MaxStayFeasibleAssignments = {}# {(day,length): {}}
		self.MinStayDesiredAssignments = {}# {(day,length): {}}
		
		# will use this to finish filling the restrictions I guess?
		self.MaxStaysFeasible = {} #{day: {length: bool}}
		
		self.OptimizeGaps = False
		
		
	def GetInitialPlan(self, checkDummyAssignments = False):
		
		newSol = Solution()
		self.OptimizationAssignments = {}
		if checkDummyAssignments:
			self.DummyOptimizedAssignment = {}
		
		if not self.Succeeded:
			return()
		
		for i in self.Inputs.StayDict:
			
			dummy = i in self.DummyStays
			if dummy and checkDummyAssignments:
				
				for j in rooms:
				
					dVal = self.Model.getVal(self.DummyAssignmentVars[i,j])
					aVal = self.Model.getVal(self.AssignmentVars[i,j])
					# Don't add this here, this is getting used 
					# for something else
					#if dVal  > 0.99:
						#print(f"got a dummy for stay {i}")
						#self.DummyOptimizedAssignment[i] = j
					newSol.DummyIncentiveValues[i,j] = dVal
					newSol.AssignmentValues[i,j] = aVal
						
			elif not dummy:
				for j in self.Inputs.Rooms:
					aVal = self.Model.getVal(self.AssignmentVars[i,j])
					if aVal > 0.99:
						self.OptimizationAssignments[i] = j
					newSol.AssignmentValues[i,j] = aVal
		self.Solutions.append(newSol)
		
		return()

	def AddDummyPlan(self, day, length):
		self.DummyOptimizedAssignments[(day,length)] = {}
		
		for i in self.Inputs.StayDict:
			if i in self.DummyStays:
				continue
			
			for j in self.Inputs.Rooms:
				if self.Model.getVal(self.AssignmentVars[i,j]) > 0.99:
					self.DummyOptimizedAssignments[(day,length)][i] = j
						
		return()

	def GenerateCliques(self):	
		self.Cliques = []
		stayDict = self.Inputs.StayDict
		for i in range(self.Inputs.MaxEnd - self.Inputs.MinStart):
			cliq = []
			for s in stayDict:
				max1 = stayDict[s][1]
				min1 = stayDict[s][0]
				if min1 <= self.Inputs.MinStart + i and max1 > self.Inputs.MinStart+i:
					cliq.append(s)
			self.Cliques.append(cliq)
		
	'''

	For the feasibility optimizations - going to bound the number of gaps below the 
	desired min night stay to the number of observed the max of the observed, 
	or the number of observed of the next smallest stay with the highest number
	(before going back down).  I.e. the goal is to replace short gaps with long 
	gaps and not increase the number of shorter gaps -- i.e. don't want to trade 
	one 3 and 2 5's for 2 4's and a 5.  

	BUT this may be overly restrictive... 
	'''
	
	def OptimizeSchedule(self, addDummyIncentives = False):
		'''
		this does the initial optimization, 
		will have another function to check feasibility. 
		'''
		start = time.time()
		
		self.GenerateCliques()
		
		self.AddAssignmentModel(addDummyIncentives, {})
		self.AddAdjacentStaysModel()
		self.AddCliqueConstraints(addDummyIncentives)
		
		obj = 0.0
		
		if self.OptimizeGaps:
			obj = quicksum(self.ObjectiveCoefficients[s]*self.AssignmentVars[s,r] for s in self.ObjectiveCoefficients for r in self.Inputs.Rooms) + 10*quicksum(self.SlackOddGroups[s,r] for s in self.AdjacentReservations for r in self.Inputs.AdjacentRooms)

		self.Model.setObjective(obj,"minimize")


		'''
		probably need to silence the output, and write it to a log
		or something... 
		'''	
		self.Model.setRealParam('limits/gap', 0.01) # stop at 99% of optimality
		self.Model.setParam('limits/time', 60) # stop after 1 minute
		
		print("Checking count of feasible sols:")
		print(self.Model.getNCountedSols())
		print()
		
		self.Model.hideOutput(True)
		self.Model.optimize()
		
		end = time.time()
		
		self.Time += (end-start)

		if self.Model.getStatus() == "infeasible": 
			# need to do a better job reading the status, just want it to be solved, 
			# and then make some report about the quality. 
			self.Succeeded = False
			self.ProvedInfeasible = self.Model.getStatus() == "infeasible"
			print(self.Model.getStatus())
			print(self.ProvedInfeasible)
			
			return()
		
		
		
		self.Succeeded = True
		return()

	
	
	def AddAssignmentModel(self, addDummyIncentiveVars, dummyLimits):
		
		for s in self.Inputs.StayDict:
			for r in self.Inputs.Rooms:
				name = str(s)+ ", " + str(r)
				self.AssignmentVars[s,r] = self.Model.addVar(name,vtype= 'B')


		for s in self.Inputs.StayDict:
			
			if s in self.Inputs.FixedRooms:
				self.Model.addCons(self.AssignmentVars[s,self.Inputs.FixedRooms[s]] == 1)
				
			if self.Inputs.GroupDict[s] == -1: # i.e. if it's a dummy stay
				
				length = self.Inputs.LengthDict[s]
				self.DummyStays.append(s)
		
				maxGaps = self.Inputs.NumberOfRooms
				
				'''
				TODO - Think about whether this is necessary! 
				Maybe can be a user input?
				
				Probably do want to check the max infeasible vs max undesirable stay,
				so could just add penalties on exceeding the bounds? 
				
				i.e. instead of hard bound on number of the small gaps, 
				hardBound + slack

				and instead of leaving out the small dummy stays, just make the penalty large.)
				
				OR can add a version that lets you check feasibility. 
				'''
				if (self.Inputs.StayDict[s][0], length) in dummyLimits:
				
					# may update the key later, this is start day and length.
					# seems like a reasonable way to store it?? 
					print("reduced the dummy limits")
					maxGaps = dummyLimits[(self.Inputs.StayDict[s][0], length)]
				
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.Rooms) <= maxGaps)
				# this incentivizes gaps longer than min stay length
				extra = 0
				if length <= self.Inputs.MinStay + 2:
					extra = 1
				
				self.ObjectiveCoefficients[s] = np.power(2.0, self.Inputs.MinStay - length + extra)
				
				if addDummyIncentiveVars:
					
				
					for r in rooms:
						self.DummyIncentiveVars[s,r] = m.addVar(name,vtype= 'B')
						self.Model.addCons(self.DummyIncentiveVars[s,r] <= self.AssignmentVars[s,r])
				
					self.Model.addCons(quicksum(self.DummyIncentiveVars[s,r] for r in self.Inputs.Rooms) <= 1)				
	
			else:
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.Rooms) == 1)
		return()
	
	
	def AddAdjacentStaysModel(self):

		slackOddGroups = {}
		adjacentReservations = []
		
		for a in self.Inputs.StayAdjacencyLists:
			aStays = self.Inputs.StayAdjacencyLists[a]
			size = len(aStays)
			# if the group has odd number, then will
			# allow one to be apart
			oddUb = 1.0
			if size <= 2:
				oddUb = 0.0
			elif size % 2 == 0:
				oddUb = 0.0


			for s in aStays:
				adjacentReservations.append(s)
				connectedStays = [cnctdStay for cnctdStay in aStays if cnctdStay != s] 
				for r in self.Inputs.RoomAdjacencyLists:
					Oname = str(s)+ ", " + str(r) + '_SlackOdd'
					slackOddGroups[s,r] = self.Model.addVar(Oname,vtype= 'B',lb = 0,ub = oddUb)
					self.Model.addCons(self.AssignmentVars[s,r] <= quicksum(self.AssignmentVars[cs,ar] for cs in connectedStays for ar in self.Inputs.RoomAdjacencyLists[r]) + slackOddGroups[s,r])
		
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for r in self.Inputs.AdjacentRooms) >= 1 - quicksum(slackOddGroups[s,r] for r in self.Inputs.AdjacentRooms))
	
			# sum of all odd slacks <= 1     
			self.Model.addCons(quicksum(slackOddGroups[s,r] for s in aStays for r in self.Inputs.AdjacentRooms) <= 1)
	
		self.SlackOddGroups = slackOddGroups
		self.AdjacentReservations = adjacentReservations
		return()
		
		
	def AddCliqueConstraints(self, addDummyIncentives):
		for r in self.Inputs.Rooms:
			#k = 0
			for c in self.Cliques:
				self.Model.addCons(quicksum(self.AssignmentVars[s,r] for s in c) == 1)
				#m.addCons(quicksum(x[s,r] for s in c) >= cvar[k])
				#k += 1
		
		if addDummyIncentives:
			for c in cliques:
				dummies = [s for s in c if s in self.DummyStays]
				self.Model.addCons(quicksum(self.DummyIncentiveVars[s,r] for s in dummies for r in self.Inputs.Rooms) <= 1)
	
		return()	
	


	