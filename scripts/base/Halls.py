# -*- coding: utf-8 -*-
import KBEngine
import Functor
from KBEDebug import *
import traceback
import GameConfigs

FIND_ROOM_NOT_FOUND = 0
FIND_ROOM_CREATING = 1

class Halls(KBEngine.Entity):
	"""
	这是一个脚本层封装的房间管理器
	"""
	def __init__(self):
		KBEngine.Entity.__init__(self)
		
		# 向全局共享数据中注册这个管理器的entityCall以便在所有逻辑进程中可以方便的访问
		KBEngine.globalData["Halls"] = self

		# 所有房间，是个字典结构，包含 {"roomEntityCall", "PlayerCount", "enterRoomReqs"}
		# enterRoomReqs, 在房间未创建完成前， 请求进入房间和登陆到房间的请求记录在此，等房间建立完毕将他们扔到space中
		self.rooms = {}
		self.lastNewRoomKey = 0

		self.Privaterooms = {}
		self.PrivatelastNewRoomKey = 0

		
	def findRoom(self, roomKey, notFoundCreate = False):
		"""
		查找一个指定房间，如果找不到允许创建一个新的
		"""
		DEBUG_MSG("Halls::findRoom : roomKey=%i notFoundCreate=%i" % (roomKey, notFoundCreate))
		roomDatas = self.rooms.get(roomKey)
		
		# 如果房间没有创建，则将其创建
		if not roomDatas:
			if not notFoundCreate:
				return FIND_ROOM_NOT_FOUND
			
			# 如果最后创建的房间没有满员，则使用最后创建的房间key，否则产生一个新的房间唯一Key
			roomDatas = self.rooms.get(self.lastNewRoomKey)
			if roomDatas is not None and roomDatas["PlayerCount"] < GameConfigs.ROOM_MAX_PLAYER:
				return roomDatas

			#生成一个64位的唯一id,作为房间的id
			self.lastNewRoomKey = KBEngine.genUUID64()
			
			# 将房间base实体创建在任意baseapp上
			# 此处的字典参数中可以对实体进行提前def属性赋值
			KBEngine.createEntityAnywhere("Room", \
									{
									"roomKey" : self.lastNewRoomKey,	\
									}, \
									Functor.Functor(self.onRoomCreatedCB, self.lastNewRoomKey))
			
			roomDatas = {"roomEntityCall" : None, "PlayerCount": 0, "enterRoomReqs" : [], "roomKey" : self.lastNewRoomKey,"userindex":{100:100}}
			self.rooms[self.lastNewRoomKey] = roomDatas
			return roomDatas

		return roomDatas
		
##########################################
	def createPrivateRoom(self, entityCall, position, direction):
			#生成一个64位的唯一id,作为房间的id
			self.PrivatelastNewRoomKey = KBEngine.genUUID64()
			
			# 将房间base实体创建在任意baseapp上
			# 此处的字典参数中可以对实体进行提前def属性赋值
			KBEngine.createEntityAnywhere("PrivateRoom", \
									{
									"roomKey" : self.PrivatelastNewRoomKey,	\
									}, \
									Functor.Functor(self.onPrivateRoomCreatedCB, self.PrivatelastNewRoomKey))
			
			roomDatas = {"roomEntityCall" : None, "PlayerCount": 0, "enterRoomReqs" : [], "roomKey" : self.PrivatelastNewRoomKey,"userindex":{100:100}}
			self.Privaterooms[self.PrivatelastNewRoomKey] = roomDatas
			roomDatas["enterRoomReqs"].append((entityCall, position, direction))

	def onPrivateRoomCreatedCB(self, roomKey, roomEntityCall):
		"""
		一个space创建好后的回调
		"""
		DEBUG_MSG("Halls::onPrivateRoomCreatedCB: space %i, entityID=%i." % (roomKey, roomEntityCall.id))
	def onPrivateRoomGetCell(self, roomEntityCall, roomKey):
		"""
		defined method.
		Room的cell创建好了
		"""
		DEBUG_MSG("Halls::onPrivateRoomGetCell: roomKey= %i." % (roomKey))
		self.Privaterooms[roomKey]["roomEntityCall"] = roomEntityCall

		# space已经创建好了， 现在可以将之前请求进入的玩家全部丢到cell地图中
		for infos in self.Privaterooms[roomKey]["enterRoomReqs"]:
			entityCall = infos[0]
			entityCall.roomKey = roomKey
			#entityCall.roomKeyc = str(roomKey)
			entityCall.createCell(roomEntityCall.cell)
			
		self.Privaterooms[roomKey]["enterRoomReqs"] = []
	def joinPrivateRoom(self,entityCall,roomkey,position, direction):
		DEBUG_MSG("Halls::joinPrivateRoom: roomKey= %i" % (roomkey))
		roomDatas = self.Privaterooms.get(roomkey)
		if not roomDatas:
			entityCall.client.onjoinPrivateRoom(0)
			return
		elif roomDatas is not None and roomDatas["PlayerCount"] < GameConfigs.ROOM_MAX_PLAYER:
			roomDatas["PlayerCount"] += 1
			roomEntityCall = roomDatas["roomEntityCall"]
			if roomEntityCall is not None:
				DEBUG_MSG(" Halls:enterRoom: existed room=%i entityID=%i" % (roomDatas["roomKey"], entityCall.id))
				entityCall.roomKey = roomEntityCall.roomKey
				roomEntityCall.enterRoom(entityCall, position, direction)
			else:
				DEBUG_MSG("Halls::enterRoom: space %i creating..., enter entityID=%i" % (roomDatas["roomKey"], entityCall.id))
				roomDatas["enterRoomReqs"].append((entityCall, position, direction))
		else:
			entityCall.client.onjoinPrivateRoom(0)
			return
	def leavePrivateRoom(self, avatarID, roomKey):
		"""
		defined method.
		某个玩家请求登出服务器并退出这个space
		"""
		#self.usedindex[avatarID]=-1
		roomDatas = self.Privaterooms.get(roomKey)
		if not roomDatas:
			DEBUG_MSG("Halls::leaveRoom: no roomDatas")
			return
		DEBUG_MSG("Halls::leaveRoom: entityID=%i roomKey=%i" % (avatarID, roomKey))
		if avatarID in roomDatas["userindex"]:
			del roomDatas["userindex"][avatarID]
		if type(roomDatas) is dict:
			roomEntityCall = roomDatas["roomEntityCall"]
			roomDatas["PlayerCount"] -= 1
			if roomEntityCall:
				roomEntityCall.leaveRoom(avatarID)
		else:
			# 由于玩家即使是掉线都会缓存至少一局游戏， 因此应该不存在退出房间期间地图正常创建中
			if roomDatas == FIND_ROOM_CREATING:
				raise Exception("FIND_ROOM_CREATING")
		DEBUG_MSG("Halls::leaveRoom PlayerCount=%i." % (roomDatas["PlayerCount"]))
	def onPrivateRoomLoseCell(self, roomKey):
		"""
		defined method.
		Room的cell销毁了
		"""
		DEBUG_MSG("Halls::onPrivateRoomLoseCell: space %i." % (roomKey))
		del self.Privaterooms[roomKey]

			
#########################################
	def enterRoom(self, entityCall, position, direction, roomKey):
		"""
		defined method.
		请求进入某个Room中
		"""
		roomDatas = self.findRoom(roomKey, True)
		DEBUG_MSG("Halls::enterRoom: PlayerCount=%i" % (roomDatas["PlayerCount"]))
		roomDatas["PlayerCount"] += 1
		index = roomDatas["PlayerCount"] % 2

		otherindex=-1
		for key,value in roomDatas["userindex"].items():
			if value:
				otherindex =key
				break
		if otherindex != -1:
			if roomDatas["userindex"][otherindex]==index:
				index = (roomDatas["PlayerCount"]+1) % 2
		roomDatas["userindex"][entityCall.id]=index
		entityCall.cellData["modelID"] = index    #+2转到我自己定义的客户端实体上
		entityCall.cellData["avatarName"] = GameConfigs.PLAYER_NAMES[index]
		entityCall.cellData["position"] = GameConfigs.PLAYER_STRAT_POINT["map1"][index]
		#roomDatas["PlayerCount"] += 1
		#self.usedindex[entityCall.id]=index

		roomEntityCall = roomDatas["roomEntityCall"]
		if roomEntityCall is not None:
			DEBUG_MSG(" Halls:enterRoom: existed room=%i entityID=%i" % (roomDatas["roomKey"], entityCall.id))
			entityCall.roomKey = roomEntityCall.roomKey
			roomEntityCall.enterRoom(entityCall, position, direction)
		else:
			DEBUG_MSG("Halls::enterRoom: space %i creating..., enter entityID=%i" % (roomDatas["roomKey"], entityCall.id))
			roomDatas["enterRoomReqs"].append((entityCall, position, direction))

	def leaveRoom(self, avatarID, roomKey):
		"""
		defined method.
		某个玩家请求登出服务器并退出这个space
		"""
		#self.usedindex[avatarID]=-1
		roomDatas = self.findRoom(roomKey, False)
		if not roomDatas:
			DEBUG_MSG("Halls::leaveRoom: no roomDatas")
			return
		DEBUG_MSG("Halls::leaveRoom: entityID=%i roomKey=%i" % (avatarID, roomKey))
		for key,value in roomDatas["userindex"].items():
			DEBUG_MSG("Halls::leaveRoom: roomDatas[userindex]=%i ,%i" % (key, value))
		if avatarID in roomDatas["userindex"]:
			del roomDatas["userindex"][avatarID]
		if type(roomDatas) is dict:
			roomEntityCall = roomDatas["roomEntityCall"]
			roomDatas["PlayerCount"] -= 1
			if roomEntityCall:
				roomEntityCall.leaveRoom(avatarID)
		else:
			# 由于玩家即使是掉线都会缓存至少一局游戏， 因此应该不存在退出房间期间地图正常创建中
			if roomDatas == FIND_ROOM_CREATING:
				raise Exception("FIND_ROOM_CREATING")
		DEBUG_MSG("Halls::leaveRoom PlayerCount=%i." % (roomDatas["PlayerCount"]))
			
	#--------------------------------------------------------------------------------------------
	#                              Callbacks
	#--------------------------------------------------------------------------------------------
	def onRoomCreatedCB(self, roomKey, roomEntityCall):
		"""
		一个space创建好后的回调
		"""
		DEBUG_MSG("Halls::onRoomCreatedCB: space %i, entityID=%i." % (roomKey, roomEntityCall.id))

	def onTimer(self, tid, userArg):
		"""
		KBEngine method.
		引擎回调timer触发
		"""
		#DEBUG_MSG("%s::onTimer: %i, tid:%i, arg:%i" % (self.getScriptName(), self.id, tid, userArg))
		pass
		
	def onRoomLoseCell(self, roomKey):
		"""
		defined method.
		Room的cell销毁了
		"""
		DEBUG_MSG("Halls::onRoomLoseCell: space %i." % (roomKey))
		del self.rooms[roomKey]

	def onRoomGetCell(self, roomEntityCall, roomKey):
		"""
		defined method.
		Room的cell创建好了
		"""
		DEBUG_MSG("Halls::onRoomGetCell: roomKey= %i." % (roomKey))
		self.rooms[roomKey]["roomEntityCall"] = roomEntityCall

		# space已经创建好了， 现在可以将之前请求进入的玩家全部丢到cell地图中
		for infos in self.rooms[roomKey]["enterRoomReqs"]:
			entityCall = infos[0]
			entityCall.roomKey = roomKey
			entityCall.createCell(roomEntityCall.cell)
			
		self.rooms[roomKey]["enterRoomReqs"] = []
	