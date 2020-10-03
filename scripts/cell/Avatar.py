# -*- coding: utf-8 -*-
import KBEngine
from KBEDebug import *
import GameUtils
import GameConfigs
import random
import copy
from interfaces.EntityCommon import EntityCommon


class Avatar(KBEngine.Entity, EntityCommon):
	def __init__(self):
		KBEngine.Entity.__init__(self)
		EntityCommon.__init__(self)
		self.startPosition = copy.deepcopy(self.position)
		self.getCurrRoom().onEnter(self)
		DEBUG_MSG("new avatar cell: id=%i accountName=%s  avatarName=%s spaceID=%i" % (self.id, self.accountName, self.avatarName, self.spaceID))
		
	def isAvatar(self):
		"""
		virtual method.
		"""
		return True
	#######################
	def onsureact(self, exposed):
		DEBUG_MSG("onsureact%i" % (self.id))
		if exposed != self.id:
			return
		room = self.getCurrRoom()
		if room:
			room.onsureact(self.id)
	def game_holds_push(self,holds):
		self.holds = holds
		if self.client:
			self.client.game_begin_push(holds)
			DEBUG_MSG('Avatar::game_holds_push=')


	######################
	#--------------------------------------------------------------------------------------------
	#                              Callbacks
	#--------------------------------------------------------------------------------------------
	def onTimer(self, tid, userArg):
		pass

	def onGetWitness(self):

		"""
		KBEngine method.
		绑定了一个观察者(客户端)
		"""
		DEBUG_MSG("Avatar::onGetWitness: %i." % self.id)
		#room = self.getCurrRoom()
		#if room:
			#if room.secondTimer>0:
			#room.updateGamestates(self.id)

	def onLoseWitness(self):
		"""
		KBEngine method.
		解绑定了一个观察者(客户端)
		"""
		DEBUG_MSG("Avatar::onLoseWitness: %i." % self.id)
	def updateStaus(self):
		room = self.getCurrRoom()
		if room:
			#room.onClientEnabled(self)
			room.updateGamestates(self.id)
	def onClientDeath(self):
		DEBUG_MSG("cellAvatar::onClientDeath: %i." % self.id)
		room = self.getCurrRoom()
		if room:
			room.onLeave(self.id)
	def isWin(self):
		room = self.getCurrRoom()
		return this.id==room.getMaxEntityID()

	def onDestroy(self):
		"""
		KBEngine method.
		entity销毁
		"""
		DEBUG_MSG("Avatar::onDestroy: %i." % self.id)
		room = self.getCurrRoom()
		
		if room:
			room.onLeaverealy(self.id)

	def newTurn(self, exposed):
		DEBUG_MSG("avavtar %i newTurn, selfID=%i" % (exposed, self.id))
		if exposed != self.id:
			return

		room = self.getCurrRoom()
		
		if room:
			room.nextPlayer()

	def reqChangeReadyState(self,exposed,STATE):
		if exposed != self.id:
			return
		room = self.getCurrRoom()
		if room:
			room.reqChangeReadyState(self.id,STATE)

	def leaveRoom(self, exposed):
		pass
	def resetGameData(self):
		self.holds = []
		#self.hitRate = 0.0
		self.totalTime = 0
		#self.totalHarm = 0
		self.score = int(0)
		#self.hitCount = 0
		#self.throwCount = 0
		#self.HP = 100

	def continueGame(self, exposed):
		DEBUG_MSG("Avatar %i continueGame" % (self.id))
		if self.id != exposed:
			return
		#self.position = copy.deepcopy(self.startPosition)
		self.client.onContinueGame(self.id)

		room = self.getCurrRoom()
		if room:
			room.addReadyPlayerCount(1, self)
			#room.reqChangeReadyState(self.id,True)
			