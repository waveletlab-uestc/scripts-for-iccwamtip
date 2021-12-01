给多个邮箱地址发送邮件，支持如下功能

1. 保存进度
2. 恢复进度

## 使用

1. 创建任务
2. 运行任务
   ```shell
   $ ./sendmail.py -t <task>
   ```
3. 保存进度，直接输入 `Ctrl-C` 自动保存任务
4. 从进度中恢复，同运行任务，会自动加载进度。如果不想使用进度，使用 `./sendmail.py -t <task> --new-task` 开始新的任务

## 提示

1. 查看 [`example-task/task.py`](example-task/task.py) 以获取如何创建任务
2. 运行后任务下会有 `log.txt` 保存运行的日志信息；`progress/` 目录保存进度信息
