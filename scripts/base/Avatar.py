# -*- coding: utf-8 -*-
import KBEngine
from KBEDebug import *
import GameConfigs
import GameUtils
import random
import json
import base64
import pyaes
#from Crypto.Cipher import AES

TIMER_TYPE_ENTER_ROOM = 1
TIMER_TYPE_DESTROY=2

class Avatar(KBEngine.Proxy):
	def __init__(self):
		KBEngine.Proxy.__init__(self)

		self.cellData["dbid"] = self.databaseID
		self.cellData["modelID" ] = 0
		self.cellData["accountName"] = self.__ACCOUNT_NAME__
		self.cellData["position"] =  None
		#self.cellData["HP"] = GameConfigs.PLAYER_HP
		#self.cellData["harmCount"] = 0
		#self.cellData["throwCount"] = 0
		#self.cellData["totalHarm"] = 0
		#self.cellData["hitCount"] = 0
		self.cellData["totalTime"] = 0
		#self.cellData["score"] = 0
		#self.cellData["hitRate"] = 0.0
		self.cellData["avatarName"] = ""

		self._destroyTimer=0
		self.isleave=False
	
		datas = self.getClientDatas()
		if datas[0]:
			try:			
				userInfo = eval(datas[0].decode())
				if 'session_key' in userInfo:
					self.sessionKey = userInfo['session_key']

				if 'openid' in userInfo:
					self.openId = userInfo['openid']
			except Exception as err:
				DEBUG_MSG("getClientDatas Error: " + str(err))

	def createCell(self, space):
		"""
		defined method.
		创建cell实体
		"""
		DEBUG_MSG("Avatar::createCellEntity: id=%i" % (self.id))
		#在这里，space指的是Room实体的CellEntityCall，也就是在Room所在的空间上创建Avatar的cell部分,这样Avatar-cell和Room-cell的spaceId是一样的
		self.createCellEntity(space)

	def destroySelf(self):
		"""
		"""
		if self.client is not None:
			return
		
		# 必须先销毁cell实体，才能销毁base
		DEBUG_MSG("Avatar::destroySelf: id=%i" % (self.id))
		if self.cell is not None:
			DEBUG_MSG("Avatar::destroyCellEntity: id=%i" % (self.id))
			self.destroyCellEntity()
			return

		KBEngine.globalData["Halls"].leaveRoom(self.id, self.roomKey)

		# 销毁base
		if(self._destroyTimer>0):
			self.delTimer(self._destroyTimer)
			self._destroyTimer=0
		DEBUG_MSG("Avatar::destroy called: id=%i" % (self.id))
		self.destroy()

	def destroySelf2(self):
		"""
		"""
		
		# 必须先销毁cell实体，才能销毁base
		DEBUG_MSG("Avatar::destroySelf: id=%i" % (self.id))
		if self.cell is not None:
			DEBUG_MSG("Avatar::destroyCellEntity: id=%i" % (self.id))
			self.destroyCellEntity()
			return

		KBEngine.globalData["Halls"].leaveRoom(self.id, self.roomKey)

		# 销毁base
		if(self._destroyTimer>0):
			self.delTimer(self._destroyTimer)
			self._destroyTimer=0
		DEBUG_MSG("Avatar::destroy called: id=%i" % (self.id))
		self.destroy()

	def onTimer(self, id, userArg):
		"""
		KBEngine method.
		使用addTimer后， 当时间到达则该接口被调用
		@param id		: addTimer 的返回值ID
		@param userArg	: addTimer 最后一个参数所给入的数据
		"""
		if TIMER_TYPE_DESTROY == userArg:
			DEBUG_MSG("TIMER_TYPE_DESTROY == userArg")
			self.destroySelf()
		if TIMER_TYPE_ENTER_ROOM == userArg:
			DEBUG_MSG("Time to Enter Room")
			self.enterRoom()
			
	def onClientEnabled(self):
		"""
		KBEngine method.
		该entity被正式激活为可使用， 此时entity已经建立了client对应实体， 可以在此创建它的
		cell部分。
		"""
		INFO_MSG("Avatar[%i] entities enable. EntityCall:%s,self.roomKey=%i" % (self.id, self.client,self.roomKey))
		#self.addTimer(1, 0, TIMER_TYPE_ENTER_ROOM)
		if self.isleave==True:
			if(self._destroyTimer>0):
				self.delTimer(self._destroyTimer)
				self._destroyTimer=0
				self.isleave=False
				self.updateStaus()
				DEBUG_MSG("Avatar:updateStaus:(self.isleave=%d)" % (self.isleave))  #加了这句影响很大，之前进不来
		#if self.cell is None:
		#	DEBUG_MSG("[%i]cell is None:" % (self.id))
		#else:
		#	self.cell.onClientEnabled()

	def updateStaus(self):
		if self.cell is not None:
			DEBUG_MSG("self.cell.updateStaus()")
			self.cell.updateStaus()

	def onLogOnAttempt(self, ip, port, password):
		"""
		KBEngine method.
		客户端登陆失败时会回调到这里
		"""
		INFO_MSG("%s login failed,Relogin here" % (self.__ACCOUNT_NAME__))
		INFO_MSG(ip, port, password)
		#self.onClientEnabled()
		return KBEngine.LOG_ON_ACCEPT
		
	def onGetCell(self):
		"""
		KBEngine method.
		entity的cell部分实体被创建成功
		"""
		#self.roomKeyc=str(self.roomKey)
		#self.roomKeyc="123456789"
		DEBUG_MSG('Avatar::onGetCell roomKey=: %i' % self.roomKey)
		
		#DEBUG_MSG('Avatar::onGetCell roomKeyc=: %s' % str(int(''.join(str(item) for item in self.roomKeyc))))

	def onLoseCell(self):
		"""
		KBEngine method.
		entity的cell部分实体丢失
		"""
		DEBUG_MSG("%s::onLoseCell: %i" % (self.className, self.id))
		#KBEngine.globalData["Halls"].leaveRoom(self.id, self.roomKey)  #从destroyself 移来-------------------------------------------------------------------------------------
		#self.roomKey=0
		self.destroySelf2()
		#self.destroySelf()
		# 如果self._destroyTimer大于0说明之前已经由base请求销毁，通常是客户端断线了
		#if self._destroyTimer > 0:
			#self.delTimer(self._destroyTimer)	
			#self._destroyTimer=0
			#self.destroySelf()
			#self.destroy()
		# 否则由cell发起销毁， 那么说明游戏结束了

	def onRestore(self):
		"""
		KBEngine method.
		entity的cell部分实体被恢复成功
		"""
		DEBUG_MSG("%s::onRestore: %s" % (self.getScriptName(), self.cell))
		
	def onClientDeath(self):
		"""
		KBEngine method.
		客户端对应实体已经销毁,客户端断线会被调用
		"""
		#断线超时了，则销毁
		DEBUG_MSG("remark Avatar[%i]  onClientDeath:" % (self.id))
		#self.destroySelf()		
		#if self.cell is None:
		#	DEBUG_MSG("remark Avatar[%i]  onClientDeath cell is None:" % (self.id))
		#else:
		#	self.cell.onClientDeath()

		self._destroyTimer=self.addTimer(17,0,TIMER_TYPE_DESTROY)
		self.isleave=True
		if self.cell is not None:
			self.cell.onClientDeath()

	#def leaverequest(self):
		#self.client=None
		#self.destroySelf()
		
		 
	def joinRoom(self):
		if self.cell is not None:
			DEBUG_MSG("avatar already has cell ")
			self.client.onclientMSG("当前房间还未退出,继续进入当前绑定的房间")
			return		
		self.enterRoom()
	def createPrivateRoom(self):
		DEBUG_MSG("avatar %i createPrivateRoom" % (self.id))
		if self.cell is not None:
			DEBUG_MSG("avatar already has cell ")
			self.client.onclientMSG("当前房间还未退出,无法创建新房间，进入当前绑定的房间")
			return
		if self.cell is None:
			# 玩家上线了或者重登陆了， 此处告诉大厅，玩家请求登陆到游戏地图中
			KBEngine.globalData["Halls"].createPrivateRoom(self, self.cellData["position"], self.cellData["direction"])
		else:
			self.updateStaus()
	def joinPrivateRoom(self,roomkey):#参数是数字数组
		#str1 = ','.join(str(i) for i in roomkey) #转成字符串
		if self.cell is not None:
			DEBUG_MSG("avatar already has cell ")
			self.client.onclientMSG("当前房间还未退出,无法加入新房间，进入当前绑定的房间")
			return
		str1=int(''.join(str(item) for item in roomkey))
		DEBUG_MSG("Halls::joinPrivateRoom roomkey= %i " % (str1))
		if self.cell is None:
			# 玩家上线了或者重登陆了， 此处告诉大厅，玩家请求登陆到游戏地图中
			KBEngine.globalData["Halls"].joinPrivateRoom(self,str1,self.cellData["position"], self.cellData["direction"])
		else:
			self.updateStaus()

	def enterRoom(self):
		# 如果玩家存在cell， 说明已经在地图中了， 因此不需要再次进入地图
		DEBUG_MSG("avatar %i enter room" % (self.id))
		if self.cell is None:
			# 玩家上线了或者重登陆了， 此处告诉大厅，玩家请求登陆到游戏地图中
			KBEngine.globalData["Halls"].enterRoom(self, self.cellData["position"], self.cellData["direction"], self.roomKey)
		else:
			self.updateStaus()

	def onDestroyTimer(self):
		DEBUG_MSG("Avatar::onDestroyTimer: %i" % (self.id))
		self.destroySelf()

	def decodeEncryptedData(self, encryptedData, iv):
		DEBUG_MSG("decodeEncryptedData")
		if not self.sessionKey:
			self.cellData["accountName"] = self.cellData["avatarName"]
			DEBUG_MSG("not sessionKey")
			return

		sessionKey = base64.b64decode(self.sessionKey)
		if len(sessionKey) < 10 :
			self.cellData["accountName"] = self.cellData["avatarName"]
			DEBUG_MSG("sessionKey invalid size")
			return
			
		encryptedData = base64.b64decode(encryptedData)
		iv = base64.b64decode(iv)

		cipher = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(sessionKey, iv))
		halfLen = int(len(encryptedData) / 2)

		try:
			datas = cipher.feed(encryptedData[:halfLen])
			datas += cipher.feed(encryptedData[halfLen:])
			datas += cipher.feed()
			decrypted = eval(datas.decode())
			DEBUG_MSG(decrypted)
			self.decryptedData = decrypted
			self.cellData["accountName"] = decrypted["nickName"]
			self.cellData["avatarUrl"]=decrypted["avatarUrl"]
			DEBUG_MSG("self.cellData[accountName] = decrypted[nickName]：%s" % self.cellData["accountName"])
			DEBUG_MSG("self.cellData[avatarUrl] = decrypted[avatarUrl]：%s" % self.cellData["avatarUrl"])
			if decrypted['watermark']['appid'] != GameConfigs.APPID:
				DEBUG_MSG("appid not equal: %s != %s" % (decrypted['watermark']['appid'], GameConfigs.APPID))
		except Exception as err:
			self.cellData["accountName"] = self.cellData["avatarName"]
			DEBUG_MSG("encry data error: " + str(err))

	