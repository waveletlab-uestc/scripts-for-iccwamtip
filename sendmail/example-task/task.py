email = {
    # 显示在对方收信邮箱上的发送者信息
    'from': 'Your Nick Name <your-email@some.com>',
    # 对方点击【回复】时，默认回复到这个邮箱
    'reply-to': 'reply-to-this@some.com',
    # 邮件标题
    'subject': 'Subject of this Email',
    # 邮件内容，@开头表示内容从文件里读取，否则使用字符串内容作为邮件内容
    'context': '@email-context.txt',
    # 附件列表
    'attaches': ['big-picture.png', 'paper.pdf']
}

accounts = [
    # 一个发送者信息
    {
        # 发送者邮箱地址
        'sender': 'your-email-address@uestc.edu.cn',
        # 用于登录 smtp 服务器的用户名，通常是邮箱名或者@前部分用户名
        'user': 'your-email-address@uestc.edu.cn',
        # 用于登录 smtp 服务器的密码
        'password': 'p@ssw0rd',
        # smtp 服务器地址和端口，这是本校的教师的邮箱服务器地址
        'smtp_server': 'mail.uestc.edu.cn',
        'smtp_port': 25,
    },

    # 另一个发送者信息
    {
        'sender': '2019xxxxxxxx@uestc.edu.cn',
        'user': '2019xxxxxxxx@uestc.edu.cn',
        'password': 'p@ssw0rd',
        # 本校学生的邮箱服务器地址
        'smtp_server': 'mail.std.uestc.edu.cn',
        'smtp_port': 25,
    },
]

address = [
    # @开头表示从文件读取邮箱列表
    '@address-list.txt',
    '@address-list2.txt',
    #一个邮箱地址
    'address@example.com',
    'email@email.com',
]
