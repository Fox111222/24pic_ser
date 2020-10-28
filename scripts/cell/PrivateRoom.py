# -*- coding: utf-8 -*-
import KBEngine
from KBEDebug import *
import GameConfigs
import random
import GameUtils

TIMER_TYPE_DESTROY = 1
TIMER_TYPE_BALANCE_MASS = 2
TIMER_TYPE_GAME_START = 3
TIMER_TYPE_NEXT_PLAYER = 4
TIMER_TYPE_GAME_OVER = 5
TIMER_TYPE_SECOND = 6
TIMER_TYPE_RESET_ROOM = 7
TIMER_TYPE_timeout =8


class PrivateRoom(KBEngine.Entity):
	"""
	游戏场景
	"""

	def __init__(self):
		KBEngine.Entity.__init__(self)

		# 把自己移动到一个不可能触碰陷阱的地方
		self.position = (999999.0, 0.0, 0.0)
		# 这个房间中所有的玩家
		self.avatars = {}
		#self.items = {}
		#self.itemspositions={}
		self.curEid = 0
		self.newTurnTimer = 0
		self.secondTimer = 0
		self.totalTime = 0
		self.readyPlayerCount = 0
		self.curSecond=30         #不要用客户端主导轮换，服务器控制
		#self.flee=0
		self.timeout=15         #玩家掉线等待时长
		self.playerMaxCount=2

		DEBUG_MSG('created space[%d] entityID = %i spaceid=%i' % (self.roomKeyC, self.id, self.spaceID))
		
		KBEngine.globalData["Room_%i" % self.spaceID] = self.base
		#self.createItems()
		###############################
		self.roomInfo = roomInfo(self.roomKeyC,self.playerMaxCount)
		self.game = None
		self.noOpData={}
		self.clearPublicRoomInfo()

		self.outcards={}
		self.sendcards=[]
		self.state = "idle";

		self.leaveAvatarHP=0
		##############################

	def onDestroy(self):
		"""
		KBEngine method.
		"""
		DEBUG_MSG("Room::onDestroy: %i" % (self.id))
		del KBEngine.globalData["Room_%i" % self.spaceID]

	def onEnter(self, entityCall):
		"""
		defined method.
		进入场景
		"""
		if(entityCall.__class__.__name__ != "Avatar"):
			return
		entityCall.roomKeyc=[]
		lis=str(self.roomKeyC)
		DEBUG_MSG("Room::onEnter: %i" % (self.roomKeyC))
		DEBUG_MSG("Room::onEnter: %s" % (lis))
		for x in lis:
			entityCall.roomKeyc.append(int(x))
		entityCall.roomKeyc=entityCall.roomKeyc
		self.avatars[entityCall.id] = entityCall
		print("Room::onEnter",entityCall.id)
		#################
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.userId == 0:
				seat.userId = entityCall.id
				seat.entity = entityCall
				break
		#################
		if len(self.avatars) == 1:
			self.curEid = entityCall.id

		#够两人了，就游戏开始
		#if len(self.avatars) == GameConfigs.ROOM_MAX_PLAYER:
		#	self.addTimer(2, 0, TIMER_TYPE_GAME_START)
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			DEBUG_MSG('self.roomInfo.seats[%d] =%d.' % (i,seat.userId))
			if seat.ready  == True:
				for entity in self.avatars.values():
					entity.client.playerReadyStateChange(seat.userId,True)

	def onTimer(self, id, userArg):
		"""
		KBEngine method.
		使用addTimer后， 当时间到达则该接口被调用
		@param id		: addTimer 的返回值ID
		@param userArg	: addTimer 最后一个参数所给入的数据
		"""
		if TIMER_TYPE_SECOND == userArg:
			self.totalTime += 1
			self.curSecond-=1
			if(self.curSecond<0):
				self.curSecond=0
		if TIMER_TYPE_NEXT_PLAYER == userArg:
			self.nextPlayer()
			

	def startGame(self):
		######################################
		self.begin()
		#######################################
		self.curEid=12345
		DEBUG_MSG("start game curEid=%i" % (self.curEid))
		self.secondTimer = self.addTimer(1, 1, TIMER_TYPE_SECOND)
		self.killNewTurnTimer()
		self.newTurn(self.curEid)
		self.flee=0
	################################################
	def begin(self):
		print("全部就位---开始处理！");
		for entity in self.avatars.values():
			entity.totals=entity.totals+1
		entitylist=list(self.avatars.values())
		self.avatar1=entitylist[0]
		self.avatar2=entitylist[1]

		self.clearPublicRoomInfo()
		self.game = MJData(self.roomInfo,self.playerMaxCount)
		self.shuffle(self.game)
		self.deal(self.game)
		self.numOfMJ = len(self.game.mahjongs) - self.game.currentIndex;
		#self.game.button=self.curEid
		#self.cur_turn = self.game.button
		self.state = "playing";
		seats = self.roomInfo.seats
		for i in range(len(seats)):
			#if seats[i].entity.client:
			seats[i].entity.game_holds_push(self.game.gameSeats[i].holds)
			DEBUG_MSG('Room::begin= %i' % i)	
				#seats[i].entity.client.upDataClientRoomInfo(self.public_roomInfo)
				#seats[i].entity.client.game_begin_push()

		print("游戏开始！");
		##游戏开始检测
		#self.gameStartCheck(self.game)
	#洗牌
	def shuffle(self,game):
		mahjongs = game.mahjongs
		#筒 (0 ~ 8 表示筒子)
		for i in range(61,113):
			mahjongs.append(i)
		#条 9 ~ 17表示条子
		# for i in range(9,18):
		# 	for c in range(4):
		# 		mahjongs.append(i)


		#万 18 ~ 26表示万
		for i in range(113,115):
			mahjongs.append(i)

		random.shuffle(mahjongs)		#随机打乱牌  洗牌

	#发牌
	def deal(self,game):
		game.currentIndex = 0	#强制清0
		#每人13张 一共 13*人数  庄家多一张 
		seatIndex = game.button
		allFPCount = 13*self.playerMaxCount
		for i in range(allFPCount):
			self.mopai(game,seatIndex)
			seatIndex +=1
			seatIndex = seatIndex%self.playerMaxCount

		#庄家多摸最后一张
		#self.mopai(game,game.button)
		#当前轮设置为庄家
		game.turn = game.button

	def mopai(self,game,seatIndex):
		if game.currentIndex == len(game.mahjongs):
			return -1
		pai = game.mahjongs[game.currentIndex]
		game.gameSeats[seatIndex].holds.append(pai)
		game.currentIndex +=1
		data = game.gameSeats[seatIndex]
		#统计牌的数目
		c = data.countMap.get(pai,None)
		if c== None:
			c=0
		data.countMap[pai] = c + 1

		return pai
	##清空游戏共享数据
	def clearPublicRoomInfo(self):
		playerList = []
		for i in range(self.playerMaxCount):
			d = {
				"userId":0,
				"folds":[],
				"angangs":[],
				"diangangs":[],
				"wangangs":[],
				"pengs":[],
				"que":-1,
				"hus":[],
				"holdsCount":0
			}
			playerList.append(d)
		data = {
			#"RoomType" : self.RoomType,
			"playerMaxCount" : self.playerMaxCount,
			"state" : "idle",
			"turn": 0,
			"numOfMJ":0,
			"button":-1,
			"playerInfo":playerList,
			"chuPai":-1
			}
		self.public_roomInfo = data
	###########################

	def newTurn(self, eeid):
		############################################
		print("newTurn",eeid)
		if(len(self.avatars)<2):
			return
		for eid,lis in self.outcards.items():
			if(len(lis)>0):
				for i in range(len(lis)):
					self.avatars[eid].holds.append(lis[i])
		self.outcards={}
		self.sendcards=[]
		for entity in self.avatars.values():
			if(len(entity.holds)<2):
				self.gameOver()
				break
			card1=entity.holds.pop(0)
			card2=entity.holds.pop(0)
			self.outcards[entity.id]=[]
			self.outcards[entity.id].append(card1)
			self.outcards[entity.id].append(card2)
			self.sendcards.append(card1)
			self.sendcards.append(card2)
			entity.holds=entity.holds
		for entity in self.avatars.values():
			entity.client.onNewTurn(eeid, GameConfigs.PLAY_TIME_PER_TURN,self.sendcards[0],self.sendcards[1],self.sendcards[2],self.sendcards[3])
			#entity.client.onNewTurn(12345, GameConfigs.PLAY_TIME_PER_TURN,self.sendcards[0],self.sendcards[1],self.sendcards[2],self.sendcards[3])
			DEBUG_MSG("client_entity %i call newturn()" % (entity.id))

		self.newTurnTimer = self.addTimer(
				GameConfigs.PLAY_TIME_PER_TURN, 0, TIMER_TYPE_NEXT_PLAYER)
		############################################
		self.curSecond=30
		#self.sendcards=[]
		
	def onsureact(self,eid):
		DEBUG_MSG("onsureact id= %i " % (eid))
		entity=self.avatars[eid]
		for id,lis in self.outcards.items():
			if(len(lis)>0):
				for i in range(len(lis)):
					entity.holds.append(lis[i])
		self.outcards={}
		entity.holds=entity.holds
		self.curEid=eid
		self.killNewTurnTimer()
		for entity in self.avatars.values():  
			if(len(entity.holds)<2):
				self.gameOver()
				return
		self.newTurn(self.curEid)
		self.curEid=0

	def getTotalTime(self):
		return self.totalTime

	def updateGamestates(self, entityID):
		DEBUG_MSG('Room::updateGamestates self.curSecond=[%d] entityID = %i.' %
		          (self.curSecond, entityID))
		if entityID in self.avatars:
			if self.state=="playing":
				self.avatars[entityID].client.updategamestuts(1)
			else:
				self.avatars[entityID].client.updategamestuts(0)
		for entity in self.avatars.values():
			if entityID in self.avatars:
				self.avatars[entityID].client.onEnterWorld2(entity.id)
		if(len(self.sendcards)>0):
			if entityID in self.avatars:
				self.avatars[entityID].holds=self.avatars[entityID].holds
				self.avatars[entityID].client.onNewTurn(entityID, self.curSecond,self.sendcards[0],self.sendcards[1],self.sendcards[2],self.sendcards[3])
		if(self.state=="idle"):
			return
		for entity in self.avatars.values():
			if(len(entity.holds)<2):
				self.gameOver()
				break
			entity.holds=entity.holds

	def onClientEnabled(self, entityCall):
		DEBUG_MSG('Room::onClientEnabled space[%d] entityID = %i.' %
		          (self.spaceID, entityCall.id))
		
		self.avatars[entityCall.id] = entityCall
		#self.killNewTurnTimer()
		if len(self.avatars)==2:
			#self.newTurn(12345)
			#self.newTurnTimer = self.addTimer(GameConfigs.PLAY_TIME_PER_TURN, 0, TIMER_TYPE_NEXT_PLAYER)
			DEBUG_MSG('Room::nextPlayer: eid=%i  newTurnTimer=%i' % (self.curEid, self.newTurnTimer))
	def onLeaverealy(self, entityID):
		"""
		defined method.
		离开场景
		"""
		DEBUG_MSG('Room::onLeaverealy space[%d] entityID = %i.' %
		          (self.spaceID, entityID))
		if entityID in self.avatars:
			self.leaveAvatarHP=self.avatars[entityID].HP
			del self.avatars[entityID]
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.userId == entityID:
				seat.userId=0
				seat.ready=False
				seat.entity=None
				break
		if(self.state=="playing"):
			self.gameOver()
		if len(self.avatars) == 0:
			self.destroy()

######################################
	def quick_chat(self,eid,idx):
		DEBUG_MSG("Room cell: quick_chat",idx)
		for entity in self.avatars.values():
			#if eid !=entity.id:
			entity.client.onquick_chat(eid,idx)     
		
	def emoji(self,eid,name):
		DEBUG_MSG("Room cell: emoji",eid,name)
		for entity in self.avatars.values():
			#if eid !=entity.id:
			entity.client.onemoji(eid,name)     
		
	def iptChat(self,eid,strstr):
		DEBUG_MSG("Room cell: iptChat",eid,strstr)
		for entity in self.avatars.values():
			#if eid !=entity.id:
			entity.client.oniptChat(eid,strstr)     
#####################################
	def onLeave(self, entityID):
		"""
		defined method.
		离开场景
		"""
		DEBUG_MSG('Room::onLeave space[%d] entityID = %i.' %
		          (self.spaceID, entityID))

		#if entityID in self.avatars:
			#del self.avatars[entityID]
		#if len(self.avatars) == 1 and self.timeout >=0 and self.flee==0:
		if len(self.avatars) == 2:
			for entity in self.avatars.values():
				entity.client.onotherNetcut(entityID)     #通知客户端有人掉线
				#self.killNewTurnTimer()
		if len(self.avatars) == 0:
			self.destroy()

	def nextPlayer(self):
		DEBUG_MSG('nextPlayer')
		self.curEid=0
		self.killNewTurnTimer()
		self.newTurn(self.curEid)
		"""
		self.newTurnTimer = self.addTimer(
			GameConfigs.PLAY_TIME_PER_TURN, 0, TIMER_TYPE_NEXT_PLAYER)
			"""
		DEBUG_MSG('Room::nextPlayer: eid=%i  newTurnTimer=%i' %
		          (self.curEid, self.newTurnTimer))
		#self.curSecond=30

	def killNewTurnTimer(self):
		DEBUG_MSG('Room::killNewTurnTimer: newTurnTimer=%i' % (self.newTurnTimer))
		if self.newTurnTimer > 0:
			self.delTimer(self.newTurnTimer)
			self.newTurnTimer = 0

	def gameOver(self):
		self.state="idle"
		self.sendcards=[]
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			seat.ready= False
		for entityID in self.avatars.keys():
			self.avatars[entityID].client.updategamestuts(0)
			"""
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			for entity in self.avatars.values():
				if seat.userId == entity.id:
					break
			seat.userId=0
			seat.entity=None
			"""
		if self.secondTimer > 0:
			self.delTimer(self.secondTimer)
			self.secondTimer = 0
		if self.newTurnTimer > 0:
			self.delTimer(self.newTurnTimer)
			self.newTurnTimer = 0
		self.settleAccount()


	#游戏算分
	def settleAccount(self):
		self.outcards={}
		keepmax=0
		Maxentity_id=-1
		for entity in self.avatars.values():
			if len(entity.holds)>keepmax:
				keepmax=len(entity.holds)
				Maxentity_id=entity.id
		for entity in self.avatars.values():
			if entity.id==self.avatar1.id:
				other=self.avatar2
			elif entity.id==self.avatar2.id:
				other=self.avatar1
			entity.holds=[]
			win = entity.id==Maxentity_id
			result = "lose"
			if win:
				result = "win"
				entity.score = entity.score+1
			DEBUG_MSG("entity id=%i is %s" % (entity.id, result))
			entity.hitRate = 0.0
			entity.totalTime = self.totalTime
			lv=1.0
			if entity.totals<entity.score:
				entity.totals=entity.score
			if (entity.totals)>0:
				lv=entity.score/(entity.totals)
			entity.client.onGameOver(
					win, entity.HP, entity.totalTime, other.HP, lv)  #输赢/抢答成功次数/总时间/对方抢答成功次数/分数

		self.resetGameState()
		entitylist=None
		self.avatar1=None
		self.avatar2=None
	def getMaxEntityID(self):
		a=0
		ID=0
		for entity in self.avatars.values():
			if(a<len(entity.holds)):
				a=len(entity.holds)
				ID=entity.id
		return ID

	def resetGameState(self):
		
		self.curEid = 12345
		self.totalTime = 0
		self.readyPlayerCount = 0
		#self.curSecond=15         #不要用客户端主导轮换，服务器控制
		self.timeout=15          #玩家掉线等待时长
		if self.newTurnTimer > 0:
			self.delTimer(self.newTurnTimer)
			self.newTurnTimer = 0
		for entity in self.avatars.values():
			entity.resetGameData()
	####################
	def reqChangeReadyState(self,callerEntityID,STATE):
		print("reqChangeReadyState",callerEntityID)
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			print(i,seat.userId,callerEntityID)
			if seat.userId ==callerEntityID:
				seat.ready = True
				#seat.entity.cell.playerReadyStateChange(seat.ready)
				print(callerEntityID,seat.ready)
				break
		for entity in self.avatars.values():
			entity.client.playerReadyStateChange(callerEntityID,STATE)
		print("len(self.roomInfo.seats)=",len(self.roomInfo.seats))
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.ready  == False:
				print(i,"seat.ready==false")
				return
		self.startGame()
	#############

	def addReadyPlayerCount(self, count, avatar):
		#self.readyPlayerCount += count
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			DEBUG_MSG('self.roomInfo.seats[%d] =%d.' % (i,seat.userId))
			if seat.ready  == True:
				for entity in self.avatars.values():
					entity.client.playerReadyStateChange(seat.userId,True)
		DEBUG_MSG("readyPlayerCount = %i" % (self.readyPlayerCount))
		#if self.readyPlayerCount >= 2:
			#self.addTimer(2, 0, TIMER_TYPE_GAME_START)



#----------------------------------------------------------------------------
#麻将信息类
class MJData:
	def __init__(self,roomInfo,maxPlayerCount):
		self.state = "idle"
		self.seatList = roomInfo.seats
		self.mahjongs = []
		self.currentIndex = 0  #当前发的牌在所有牌中的索引
		self.button = 0 #庄家位置
		self.turn = 0  #记录该谁出牌
		self.chuPai = -1
		self.gameSeats = []
		for i in range(maxPlayerCount):	
			seat = seatData(self,i,self.seatList[i])
			self.gameSeats.append(seat)


#所有玩家的牌类信息
class seatData:
	def __init__(self,game,index,seat):
		self.entity = seat.entity; #玩家实体
		self.game = game   #游戏对象
		self.seatIndex = index   #玩家座位索引
		self.userId =seat.userId		#玩家id
		self.holds = []  #持有的牌
		self.folds = []  #打出的牌
		self.tingMap = {} #玩家手上的牌的数目，用于快速判定碰杠
		self.countMap = {}  #玩家手上的牌的数目，用于快速判定碰杠
		self.que = -1 #缺一门
		self.canChuPai = False #是否可以出牌
		self.canGang = False #是否可以杠
		self.gangPai = [] #用于记录玩家可以杠的牌
		self.canHu = False #是否可以胡
		self.canPeng = False #是否可以碰
		self.hued = False
		self.pengs = [] #碰了的牌
		self.angangs = [] #暗杠的牌
		self.diangangs = [] #点杠的牌
		self.wangangs = [] #弯杠的牌
		self.hus = [] #胡了的牌

#房间信息
class roomInfo:
	def __init__(self,roomKey,maxPlayerCount):
		self.id = roomKey
		self.seats = []
		for i in range(maxPlayerCount):
			seat = seat_roomInfo(i)
			self.seats.append(seat)

	def clearData(self):
		for i in range(len(self.seats)):
			self.clearDataBySeat(i,False)

	def clearDataBySeat(self,index,isOut = True):
		s = self.seats[index]
		if isOut:
			s.userId = 0
			s.entity = None
		s.ready = False
		#s.score = int(0)
		s.seatIndex = index

	def clearDataByEntityID(self,entityID,isOut = True):
		for i in range(len(self.seats)):
			if self.seats[i].userId == entityID:
				self.clearDataBySeat(i,isOut)
				break



#椅子信息
class seat_roomInfo:
	def __init__(self,seatIndex):
		self.userId = 0
		self.entity = None
		#self.score = int(0)
		self.ready = False
		self.seatIndex = seatIndex
