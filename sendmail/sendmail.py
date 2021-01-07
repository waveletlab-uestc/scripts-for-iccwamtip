#!/usr/bin/env python3

import re
import smtplib
import mimetypes
import sys
from time import sleep
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from email.header import Header

import config

account = config.accounts[0]

def read_receivers(address_file):
    with open(address_file) as fp:
        return [addr.strip() for addr in fp.readlines()]

class Message:
    def __init__(self, from_, subject, context, attaches=None, reply_to='icacia@uestc.edu.cn'):
        sender_info = re.match(r'\s*(.+?)\s*<([-_\w.]+@[-_\w.]+\.\w+)>', from_)
        sender_name = sender_info[1]
        sender_addr = sender_info[2]
        message = MIMEMultipart()
        message['From'] = formataddr([sender_name, sender_addr])
        message['Subject'] = Header(subject)
        message['Reply-To'] = reply_to

        # 正文
        with open(context, 'r') as fp:
            message.attach(MIMEText(fp.read(), 'plain', 'utf-8'))

        # 附件
        attaches = attaches or []
        for attach_file in attaches:
            with open(attach_file, 'rb') as fp:
                attach = MIMEText(fp.read(), 'base64', 'utf-8')
                # replace default Content-Type 'text/base64; charset=utf-8' to file mimetype
                attach.replace_header('Content-Type', mimetypes.guess_type(attach_file)[0])
                attach['Content-Disposition'] = 'attachment; filename="{}"'.format(attach_file)
                message.attach(attach)

        self._message = message


    def to(self, to_addr):
        try:
            self._message.replace_header('To', to_addr)
        except KeyError:
            self._message.add_header('To', to_addr)
        return self

    def as_string(self):
        return self._message.as_string()


class Smtp:
    def __init__(self, account):
        self._account = account
        self._emails_per_connection = 5
        self._login()

    def _login(self):
        self._closed = False
        self._smtp = smtplib.SMTP(self._account['smtp_server'], self._account['smtp_port'])
        self._smtp.login(self._account['user'], self._account['password'])
        self._emails_on_connection = 0

    def _relogin(self):
        self.close()
        self._login()

    def sendmail(self, to_addr, msg):
        if self._closed:
            self._login()
        if self._emails_on_connection >= self._emails_per_connection:
            self._relogin()
        try:
            self._emails_on_connection += 1
            self._smtp.sendmail(self._account['addr'], to_addr, msg)
        except smtplib.SMTPResponseException as e:
            self.close()
            raise e

    def close(self):
        self._closed = True
        self._smtp.close()

def main(addresses=None):
    if not addresses:
        addresses = './address.txt'
    subject = '[请补充发票信息] 2020 the 17th ICCWAMTIP Conference'
    context = './copyright.msg'
    #attaches = []

    receivers = read_receivers(addresses)
    message = Message(account['from'], subject, context)

    WAIT_TIME = 1*60
    wait_time = WAIT_TIME

    time_out = 1
    fail_cnt = 0
    sucess_cnt = 0
    force_quit = False

    smtp = Smtp(account)

    idx = 0
    while idx < len(receivers) and not force_quit:
        receiver = receivers[idx]
        try:
            smtp.sendmail(receiver, message.to(receiver).as_string())
            print("{}. send email to {}".format(idx, receiver))
            sucess_cnt += 1
            time_out = 1
            wait_time = WAIT_TIME
        except smtplib.SMTPException as e:
            print("{}. send email to {} fail".format(idx, receiver), e)
            print("  {}. wait {} seconds try again ...".format(idx, wait_time))
            idx -= 1
            time_out = wait_time
            wait_time *= 2

        idx += 1

        try:
            sleep(time_out)
        except (InterruptedError, KeyboardInterrupt):
            force_quit = True


    smtp.close()
    print("send over. sucess: {}/{}".format(sucess_cnt, idx))


def usage():
    print("sendmail.py [<address-file>]")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    main(sys.argv[1])
