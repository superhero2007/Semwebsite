
import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

class Email(object):
    def __init__(self,
                 smtp_server = os.environ.get('SMTP_Server'),
                 smtp_port = os.environ.get('SMTP_Port'),
                 smtp_username = os.environ.get('SMTP_UserName'),
                 smtp_password = os.environ.get('SMTP_Password')):

        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port)
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password

        # error check
        if self.smtp_server==None:
            logging.error('No SMTP Server defined')
            raise Exception

    def send_email(self,email_to,subject,content='',attachments=[],email_from=None):
        #set email_from
        email_from = self.smtp_username if email_from == None else email_from

        # construct content
        msg = MIMEMultipart()
        part1 = MIMEText(content, 'html')
        msg.attach(part1)
        #msg = MIMEText(DATA)
        msg['Subject'] = subject
        msg['To'] = ", ".join(email_to)
        msg['From'] = email_from

        for f in attachments:
            with open(f, "rb") as fil:
                msg.attach(MIMEApplication(
                    fil.read(),
                    Content_Disposition='attachment; filename="%s"' % os.path.basename(f),
                    Name=os.path.basename(f)
                ))
        mail = smtplib.SMTP(self.smtp_server, self.smtp_port)
        mail.starttls()
        mail.login(self.smtp_username, self.smtp_password)
        mail.sendmail(email_from, email_to, msg.as_string())
        mail.quit()

