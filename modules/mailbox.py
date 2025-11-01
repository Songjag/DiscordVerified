class MailBox:
    def __init__(self):
        pass
    def mailto(self,option,code:str)->str:
        file=None
        if option=="register":
            file="mail/register.mailbox"
        elif option=="resetpassword":
            file="mail/resetpassword.mailbox"
        else:
            file="mail/login.mailbox"
        with open(file,'r',encoding="utf-8") as f:
            data=f.read()
        return data.replace('{code}',code)
