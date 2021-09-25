#!/usr/bin/env python3

import re
import os
import smtplib
import mimetypes
import argparse
import importlib.util
from collections import deque
from time import sleep
from contextlib import closing
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from email.header import Header


def _cat(fname, mode='r'):
    """读取文件 fname 的内容"""
    with open(fname, mode) as fp:
        return fp.read()


def _parse_and_read(string, mode='r', prefix='@'):
    """如果 string 以 prefix 作为前缀，
    那么读取 string 去掉 prefix 前缀后的文件的内容
    否则，直接返回 string
    """
    if not string.startswith(prefix):
        return string
    return _cat(string.lstrip(prefix), mode)


class Message:
    """邮件正文内容"""
    def __init__(self, from_, subject, context, attaches=None, reply_to=None):
        sender_info = re.match(r'\s*(.+?)\s*<([-_\w.]+@[-_\w.]+\.\w+)>', from_)
        sender_name = sender_info[1]
        sender_addr = sender_info[2]
        message = MIMEMultipart()
        message['From'] = formataddr([sender_name, sender_addr])
        message['Subject'] = Header(subject)
        message['Reply-To'] = reply_to if reply_to else sender_addr

        # 正文
        message.attach(MIMEText(context, 'plain', 'utf-8'))

        # 附件
        attaches = attaches or []
        for attach_path in attaches:
            attach = MIMEText(_cat(attach_path, 'rb'), 'base64', 'utf-8')
            # replace default Content-Type 'text/base64; charset=utf-8' to file mimetype
            attach.replace_header('Content-Type', mimetypes.guess_type(attach_path)[0])
            attach['Content-Disposition'] = 'attachment; filename="{}"'.format(os.path.basename(attach_path))
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
        self._emails_on_connection = 0
        self._closed = True

    def _login(self):
        self._smtp = smtplib.SMTP(self._account['smtp_server'], self._account['smtp_port'])
        self._smtp.login(self._account['user'], self._account['password'])
        self._closed = False

    def _relogin(self):
        self.close()
        self._login()

    @property
    def sender(self):
        return self._account['sender']

    def sendmail(self, to_addr, msg):
        if self._closed:
            self._login()
        if self._emails_on_connection >= self._emails_per_connection:
            self._relogin()
        self._emails_on_connection += 1
        try:
            self._smtp.sendmail(self.sender, to_addr, msg)
        except smtplib.SMTPResponseException as e:
            self._emails_on_connection += 1
            self.close()
            raise e

    def close(self):
        if not self._closed:
            self._smtp.close()
        self._closed = True


class Task:
    def __init__(self, cfg, workdir):
        self._workdir = workdir
        self._email = cfg.email
        self._accounts = cfg.accounts
        self._receivers = deque(Task._merge_receivers(cfg.address))
        self._sent = set()
        self._failed = set()
        self._message = Message(self._email['from'], self._email['subject'],
                _parse_and_read(self._email['context']),
                self._email['attaches'], self._email['reply-to'])
        self._wait_time = 1*60  # 所有账户都发送失败，然后等待 1 分钟然后再重试
        self._time_out = 1      # 每封邮件之间发送等待间隔 1 秒钟
        self._log_fp = open(os.path.join(workdir, 'log.txt'), 'a')

    @staticmethod
    def load_config(path):
        task_path = os.path.join(path, 'task.py')
        spec = importlib.util.spec_from_file_location('module.name', task_path)
        task = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task)
        # 修正路径，添加前缀
        if task.email['context'].startswith('@'):
            task.email['context'] = '@' + os.path.join(path, task.email['context'][1:])
        task.email['attaches'] = [os.path.join(path, attach) for attach in task.email['attaches']]
        addresses = []
        for file in task.address:
            if file.startswith('@'):
                addresses.append('@' + os.path.join(path, file[1:]))
            else:
                addresses.append(file)
        task.address = addresses
        return task

    def run(self):
        no = len(self._sent) + len(self._failed) + 1
        idx = 0
        suspend_accounts = set()
        wait_time = self._wait_time
        sent_cnt = 0
        failed_cnt = 0
        force_quit = False
        while self._receivers and not force_quit:
            if len(suspend_accounts) == len(self._accounts):
                suspend_accounts.clear()
                self.save_progress()        # 保存一下进度
                self.log("All accounts are suspended, wating {} second then re-try ...".format(wait_time))
                try:
                    sleep(wait_time)
                except (InterruptedError, KeyboardInterrupt):
                    break
                wait_time *= 2
            account = self._accounts[idx]
            self.log("Using account {} to send emails".format(account['sender']))
            with closing(Smtp(account)) as smtp:
                force_quit, cnt, cnt2 = self._send_mail(smtp, no)
            if cnt + cnt2 == 0:
                suspend_accounts.add(idx)
            else:
                wait_time = self._wait_time
            sent_cnt += cnt
            failed_cnt += cnt2
            no += cnt + cnt2
            idx = (idx + 1) % len(self._accounts)

        self.save_progress()

        rest_total = sent_cnt + failed_cnt + len(self._receivers)  # 本次任务剩下应发送的
        all_cnt = len(self._sent)                  # 所有已发送的
        all_total = all_cnt + len(self._receivers) # 所有应该发送的
        self.log("Sent over. sent {}/{} ({:.2f}%), total {}/{} ({:.2f}%).".format(
            sent_cnt + failed_cnt, rest_total,
            100 if rest_total == 0 else (sent_cnt + failed_cnt)/rest_total * 100,
            all_cnt, all_total, 100 if all_total == 0 else all_cnt/all_total * 100))

        self.quit()


    def save_progress(self):
        """保存已发送邮件的地址到
        task_dir/progress/{sucess_sent,failed_sent,rest_receivers}.txt
        文件里
        """
        progress_path = os.path.join(self._workdir, 'progress')
        os.makedirs(progress_path, exist_ok=True)
        sucess_path = os.path.join(progress_path, 'sucess_sent.txt')
        failed_path = os.path.join(progress_path, 'failed_sent.txt')
        rest_path = os.path.join(progress_path, 'rest_receivers.txt')
        for file, addrs in [(sucess_path, self._sent),
                (failed_path, self._failed),
                (rest_path, self._receivers)]:
            with open(file, 'w') as fp:
                fp.write('\n'.join(addrs))

    def load_progress(self):
        progress_path = os.path.join(self._workdir, 'progress')
        if not os.path.isdir(progress_path):
            return False

        sucess_path = os.path.join(progress_path, 'sucess_sent.txt')
        failed_path = os.path.join(progress_path, 'failed_sent.txt')
        rest_path = os.path.join(progress_path, 'rest_receivers.txt')
        if (not os.path.isfile(sucess_path)
                or not os.path.isfile(failed_path)
                or not os.path.isfile(rest_path)):
            return False
        self._sent = set(Task._read_receivers(sucess_path))
        self._failed = set(Task._read_receivers(failed_path))
        # 合并邮件地址，以支持动态添加新地址
        new_receivers = set(self._receivers)
        rest_receivers = [x for x in Task._read_receivers(rest_path) if x not in new_receivers]
        self._receivers += rest_receivers
        return True

    def clear_log(self):
        self._log_fp.truncate(0)

    def log(self, *values):
        print(*values)
        print(*values, file=self._log_fp)

    def quit(self):
        self._log_fp.close()


    def _not_sent(self, addr):
        return addr not in self._sent and addr not in self._failed


    def _send_mail(self, smtp, no):
        sent_cnt = 0
        failed_cnt = 0
        force_quit = False
        while self._receivers:
            receiver = self._receivers.popleft()
            if self._not_sent(receiver):
                try:
                    smtp.sendmail(receiver, self._message.to(receiver).as_string())
                    #raise Exception('for test')
                except (InterruptedError, KeyboardInterrupt):
                    self._receivers.appendleft(receiver)
                    force_quit = True
                    break
                except Exception as e:
                    self.log("{}. {} sent email to {} fail".format(no, smtp.sender, receiver), e)
                    if isinstance(e, smtplib.SMTPRecipientsRefused) and 'User not found' in e.recipients:
                        self.log("{}. {} sent email to invalid address {}".format(no, smtp.sender, receiver))
                        self._failed.add(receiver)
                        failed_cnt += 1
                    else:
                        self._receivers.appendleft(receiver)
                    break
                self.log("{}. {} sent email to {}".format(no, smtp.sender, receiver))
                no += 1
                sent_cnt += 1
                self._sent.add(receiver)

                try:
                    # 等待 self._time_out 秒，再发送下一封邮件
                    sleep(self._time_out)
                except (InterruptedError, KeyboardInterrupt):
                    force_quit = True
                    break

        return force_quit, sent_cnt, failed_cnt


    @staticmethod
    def _read_receivers(file):
        with open(file) as fp:
            return [addr.strip() for addr in fp.readlines()]

    @staticmethod
    def _merge_receivers(addresses):
        receivers = []

        for addr in addresses:
            if addr.startswith('@'):
                receivers += Task._read_receivers(addr[1:])
            else:
                receivers.append(addr)
        return receivers


def args_parser():
    parser = argparse.ArgumentParser(description='给批量用户发送邮件')
    parser.add_argument('-t', '--task',
            action='store',
            required=True,
            help="运行指定的任务")
    parser.add_argument('-n', '--new-task',
            action='store_true',
            default=False,
            help="如果任务保存得有进度，仍然重新开始运行任务 (默认继续运行任务)")
    return parser.parse_args()


def main():
    args = args_parser()

    task_cfg = Task.load_config(args.task)
    task = Task(task_cfg, args.task)
    if args.new_task:
        task.clear_log()
    else:
        ok = task.load_progress()
        if not ok:
            print("Start a new task")
    task.run()


if __name__ == '__main__':
    main()
