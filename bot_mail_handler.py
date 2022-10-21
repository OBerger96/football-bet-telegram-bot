from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import smtplib


def send_db_to_bot_email():
    mail_content = 'BetBot sent newest DB image'
    sender_address = 'betbot2819@gmail.com'
    sender_pass = 'euro2021!'
    receiver_address = 'betbot2819@gmail.com'
    message = MIMEMultipart()
    message['From'] = sender_address
    message['To'] = receiver_address
    message['Subject'] = 'FIFA World Cup newest DB'
    message.attach(MIMEText(mail_content, 'plain'))
    attach_file_name = 'euro2021bets.db'
    attach_file = open(attach_file_name, 'rb')
    payload = MIMEBase('application', 'octate-stream')
    payload.set_payload(attach_file.read())
    encoders.encode_base64(payload)
    payload.add_header('Content-Decomposition', 'attachment', filename=attach_file_name)
    message.attach(payload)
    session = smtplib.SMTP('smtp.gmail.com', 587)
    session.starttls()
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    print('Mail Sent')


if __name__ == "__main__":
    send_db_to_bot_email()
