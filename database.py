from pymongo import MongoClient
import config
from datetime import datetime 


client = MongoClient(config.DATABASE_URI)
db = client["BotInvestor"]
users = db["users"]
bot_setting = db["bot_setting"]


class Permission:
    USE_BOT = "use_bot"
    SEND_MESSAGES = "send_messages"
    BAN_USERS = "ban_users"
    SEE_PROFILE = "see_profiles"
    ADD_ADMIN = "add_admin"
    MANAGE_BOT = "manage_bot"
    ADMIN_PERMISSION = {
            USE_BOT: True, SEND_MESSAGES: True, BAN_USERS: True, ADD_ADMIN: True,
            SEE_PROFILE: True, MANAGE_BOT: True
    }
    
    USER_PERMISSION = {
            USE_BOT: True, SEND_MESSAGES: False, BAN_USERS: False, ADD_ADMIN: False,
            SEE_PROFILE: False, MANAGE_BOT: False
    }
    
    
class User:

    def __init__(self, id):
        self.id = id
        self.__fetch_user(self.id)
        
        
    @classmethod
    def insert(cls, id):
        """
        Save new user into database.
        :param id[int]
        """
        if id == config.ADMIN_ID:
            status = "admin"
            perm = Permission.ADMIN_PERMISSION
        else:
            status = "user"
            perm = Permission.USER_PERMISSION
            
        kw = {"id": id, "date": datetime.utcnow(), "withdraw": 0, "invest": 0, "profit": 0, 
              "withdraw_history": [], "invest_history": [], "status": status, "permission": perm, "balance": 0
        }
        
        users.insert_one(kw)
    
    def __fetch_user(self, id):
        user = users.find_one({"id": id})
        if user is None:
            self.permission = None
            self.status = None
            return
        self.date = user.get("date")
        self.withdraw = user.get("withdraw")
        self.invest = user.get("invest")
        self.withdraw_history: list[dict] = user.get("withdraw_history")
        self.invest_history: list[dict] = user.get("invest_history")
        self.status: str = user.get("status")
        self.permission: dict = user.get("permission")
        self.balance = user.get("balance") 
        self.hash = user.get("_id")
        
        if self.hash: self.hash = self.hash.__str__()
        
    def can(self, perm: Permission):
        if self.permission is None: 
            return False
        else:
            return self.permission.get(perm, False) is True
          
              
    def update(self, **kwargs):
        users.update_one({"id": self.id}, {"$set": kwargs})
     
    @staticmethod       
    def find_one(**kwargs):
        return users.find_one(kwargs)
    
    def exist(self):
        return self.permission is not None
        
    @staticmethod
    def find(**kwargs): 
        return [u for u in users.find(kwargs)]
        
    def has_all_permission(self):
        return all([perm == True for k, perm in self.permission.items()])


class BotSetting:
   def __init__(self):
       setting = bot_setting.find_one({})
       self.channels: list[dict] = setting.get("channels")
       self.payeer: list[str] = setting.get("payeer")
       self.usdt: list[str] = setting.get("usdt")
       self._id = setting.get("_id")
        
   @staticmethod
   def insert():
       setting = bot_setting.find_one({}) 
       if not setting:
           kw = {"channels": [], "payeer": [], "usdt": []}
           bot_setting.insert_one(kw)
      
                
   def update(cls, **kwargs):
        print(kwargs)
        bot_setting.update_one({"_id": cls._id}, {"$set": kwargs})
   
   

if __name__ == '__main__':
    users.delete_many({})
    BotSetting.insert()
       
   
   
        
    
        