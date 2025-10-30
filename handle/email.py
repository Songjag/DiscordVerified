from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from modules.sql import CAioMysql
from modules.mailbox import MailBox
from random import randint
import asyncio
class Server():
    def __init__(self):
        self.database=CAioMysql()
        asyncio.run(self.on_ready())
    async def on_ready(self):
        await self.database.connected('core')
    async def check_user(self,gmail,password)->bool:
        a=await self.database.fetchone('SELECT password from users where gmail=%s',(gmail,))
        if a:
            return a[0]==password
        else:
            return False     
    def login(self,gmail,password):
        asyncio.run(self.check_user(gmail=gmail,password=password))
    def create_code(self)->int:
        return randint(100000,999999)
        

class Register(Server):
    def __init__(self):
        self.mailbox=MailBox()
    def send_mail(self,gmail,option):
        data=self.mailbox.mailto(option)
        

        