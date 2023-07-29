# encoding:utf-8
import threading

import plugins
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from channel.wechat.wechat_channel import WechatChannel

from common.log import logger
from common.expired_dict import ExpiredDict
from config import conf
from PIL import Image
from apscheduler.schedulers.blocking import BlockingScheduler

from plugins import *
import base64
import os
import io
import requests


@plugins.register(
    name="Midjourney",
    desire_priority=-1,
    hidden=False,
    desc="AI drawing plugin of midjourney",
    version="1.0",
    author="litter-coder",
)
class Midjourney(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.proxy_server = conf().get("proxy_server")
        self.proxy_api_secret = conf().get("proxy_api_secret")
        self.channel = WechatChannel()
        self.task_id_dict = ExpiredDict(60 * 60)
        self.cmd_dict = ExpiredDict(60 * 60)
        scheduler = BlockingScheduler()
        scheduler.add_job(self.query_task_result, 'interval', seconds=10)
        # 创建并启动一个新的线程来运行调度器
        thread = threading.Thread(target=scheduler.start)
        thread.start()
        logger.info("[Midjourney] inited")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [ContextType.TEXT, ContextType.IMAGE]:
            return
        content = e_context["context"].content
        msg: ChatMessage = e_context["context"]["msg"]
        if not e_context["context"]["isgroup"]:
            state = "u:" + msg.other_user_id + ":" + msg.other_user_nickname
        else:
            state = "r:" + msg.other_user_id + ":" + msg.actual_user_nickname
        result = None
        try:
            if content.startswith("/imagine "):
                result = self.handle_imagine(content[9:], state)
            elif content.startswith("/up "):
                arr = content[4:].split()
                try:
                    task_id = arr[0]
                    index = int(arr[1])
                except Exception as e:
                    e_context["reply"] = Reply(ReplyType.TEXT, '❌ 您的任务提交失败\nℹ️ 参数错误')
                    e_context.action = EventAction.BREAK_PASS
                    return
                # 获取任务
                task = self.get_task(task_id)
                if task is None:
                    e_context["reply"] = Reply(ReplyType.TEXT, '❌ 您的任务提交失败\nℹ️ 任务ID不存在')
                    e_context.action = EventAction.BREAK_PASS
                    return
                if index > len(task['buttons']):
                    e_context["reply"] = Reply(ReplyType.TEXT, '❌ 您的任务提交失败\nℹ️ 按钮序号不正确')
                    e_context.action = EventAction.BREAK_PASS
                    return
                # 获取按钮
                button = task['buttons'][index - 1]
                if button['label'] == 'Custom Zoom':
                    e_context["reply"] = Reply(ReplyType.TEXT, '❌ 您的任务提交失败\nℹ️ 暂不支持自定义变焦')
                    e_context.action = EventAction.BREAK_PASS
                    return
                result = self.post_json('/submit/action',
                                        {'customId': button['customId'], 'taskId': task_id, 'state': state})
            elif content.startswith("/img2img "):
                self.cmd_dict[msg.actual_user_id] = content
                e_context["reply"] = Reply(ReplyType.TEXT, '请给我发一张图片作为垫图')
                e_context.action = EventAction.BREAK_PASS
                return
            elif content == "/describe":
                self.cmd_dict[msg.actual_user_id] = content
                e_context["reply"] = Reply(ReplyType.TEXT, '请给我发一张图片用于图生文')
                e_context.action = EventAction.BREAK_PASS
                return
            elif content.startswith("/shorten "):
                result = self.handle_shorten(content[9:], state)
            elif e_context["context"].type == ContextType.IMAGE:
                cmd = self.cmd_dict.get(msg.actual_user_id)
                if not cmd:
                    return
                msg.prepare()
                self.cmd_dict.pop(msg.actual_user_id)
                if "/describe" == cmd:
                    result = self.handle_describe(content, state)
                elif cmd.startswith("/img2img "):
                    result = self.handle_img2img(content, cmd[9:], state)
                else:
                    return
            else:
                return
        except Exception as e:
            logger.exception("[Midjourney] handle failed: %s" % e)
            result = {'code': -9, 'description': '服务异常, 请稍后再试'}
        code = result.get("code")
        if code == 1:
            task_id = result.get("result")
            self.add_task(task_id)
            e_context["reply"] = Reply(ReplyType.TEXT,
                                       '✅ 您的任务已提交\n🚀 正在快速处理中，请稍后\n📨 任务ID: ' + task_id)
        elif code == 22:
            self.add_task(result.get("result"))
            e_context["reply"] = Reply(ReplyType.TEXT, '✅ 您的任务已提交\n⏰ ' + result.get("description"))
        else:
            e_context["reply"] = Reply(ReplyType.TEXT, '❌ 您的任务提交失败\nℹ️ ' + result.get("description"))
        e_context.action = EventAction.BREAK_PASS

    def handle_imagine(self, prompt, state):
        return self.post_json('/submit/imagine', {'prompt': prompt, 'state': state})

    def handle_describe(self, img_data, state):
        base64_str = self.image_file_to_base64(img_data)
        return self.post_json('/submit/describe', {'base64': base64_str, 'state': state})

    def handle_shorten(self, prompt, state):
        return self.post_json('/submit/shorten', {'prompt': prompt, 'state': state})

    def handle_img2img(self, img_data, prompt, state):
        base64_str = self.image_file_to_base64(img_data)
        return self.post_json('/submit/imagine', {'prompt': prompt, 'base64': base64_str, 'state': state})

    def post_json(self, api_path, data):
        return requests.post(url=self.proxy_server + api_path, json=data,
                             headers={'mj-api-secret': self.proxy_api_secret}).json()

    def get_task(self, task_id):
        return requests.get(url=self.proxy_server + '/task/%s/fetch' % task_id,
                            headers={'mj-api-secret': self.proxy_api_secret}).json()

    def add_task(self, task_id):
        self.task_id_dict[task_id] = 'NOT_START'

    def query_task_result(self):
        task_ids = list(self.task_id_dict.keys())
        logger.info("[Midjourney] handle task , size [%s]", len(task_ids))
        if len(task_ids) == 0:
            return
        tasks = self.post_json('/task/list-by-condition', {'ids': task_ids})
        for task in tasks:
            task_id = task['id']
            description = task['description']
            status = task['status']
            action = task['action']
            state_array = task['state'].split(':', 2)
            context = Context()
            context.__setitem__("receiver", state_array[1])
            if state_array[0] == 'r':
                reply_prefix = '@%s ' % state_array[2]
            else:
                reply_prefix = ''
            if status == 'SUCCESS':
                logger.debug("[Midjourney] 任务已完成: " + task_id)
                self.task_id_dict.pop(task_id)
                if action == 'DESCRIBE' or action == 'SHORTEN':
                    prompt = task['properties']['finalPrompt']
                    reply = Reply(ReplyType.TEXT, (
                                reply_prefix + '✅ 任务已完成\n📨 任务ID: %s\n%s\n\n' + self.get_buttons(
                            task) + '\n' + '💡 使用 /up 任务ID 序号执行动作\n🔖 /up %s 1') % (
                                      task_id, prompt, task_id))
                    self.channel.send(reply, context)
                elif action == 'UPSCALE':
                    reply = Reply(ReplyType.TEXT,
                                  ('✅ 任务已完成\n📨 任务ID: %s\n✨ %s\n\n' + self.get_buttons(
                                      task) + '\n' + '💡 使用 /up 任务ID 序号执行动作\n🔖 /up %s 1') % (
                                      task_id, description, task_id))
                    url_reply = Reply(ReplyType.IMAGE_URL, task['imageUrl'])
                    self.channel.send(url_reply, context)
                    self.channel.send(reply, context)
                else:
                    reply = Reply(ReplyType.TEXT,
                                  ('✅ 任务已完成\n📨 任务ID: %s\n✨ %s\n\n' + self.get_buttons(
                                      task) + '\n' + '💡 使用 /up 任务ID 序号执行动作\n🔖 /up %s 1') % (
                                      task_id, description, task_id))
                    image_storage = self.download_and_compress_image(task['imageUrl'])
                    url_reply = Reply(ReplyType.IMAGE, image_storage)
                    self.channel.send(url_reply, context)
                    self.channel.send(reply, context)
            elif status == 'MODAL':
                res = self.post_json('/submit/modal', {'taskId': task_id})
                if res.get("code") != 1:
                    self.task_id_dict.pop(task_id)
                    reply = Reply(ReplyType.TEXT,
                                  reply_prefix + '❌ 任务执行失败\n✨ %s\n📨 任务ID: %s\n📒 失败原因: %s' % (
                                  description, task_id, res.get("description")))
                    self.channel.send(reply, context)
            elif status == 'FAILURE':
                self.task_id_dict.pop(task_id)
                reply = Reply(ReplyType.TEXT,
                              reply_prefix + '❌ 任务执行失败\n✨ %s\n📨 任务ID: %s\n📒 失败原因: %s' % (
                              description, task_id, task['failReason']))
                self.channel.send(reply, context)

    def image_file_to_base64(self, file_path):
        with open(file_path, "rb") as image_file:
            img_data = image_file.read()
        img_base64 = base64.b64encode(img_data).decode("utf-8")
        os.remove(file_path)
        return "data:image/png;base64," + img_base64

    def get_buttons(self, task):
        res = ''
        index = 1
        for button in task['buttons']:
            name = button['emoji'] + button['label']
            if name in ['🎉Imagine all', '❤️']:
                continue
            res += ' %d- %s\n' % (index, name)
            index += 1
        return res

    def download_and_compress_image(self, img_url, max_size=(800, 800)):  # 下载并压缩图片
        # 下载图片
        pic_res = requests.get(img_url, stream=True)
        image_storage = io.BytesIO()
        for block in pic_res.iter_content(1024):
            image_storage.write(block)
        image_storage.seek(0)

        # 压缩图片
        initial_image = Image.open(image_storage)
        initial_image.thumbnail(max_size)
        output = io.BytesIO()
        initial_image.save(output, format=initial_image.format)
        output.seek(0)
        return output

    def get_help_text(self, verbose=False, **kwargs):
        help_text = "这是一个能调用midjourney实现ai绘图的扩展能力。\n"
        if not verbose:
            return help_text
        help_text += "使用说明: \n"
        help_text += "/imagine 根据给出的提示词绘画;\n"
        help_text += "/img2img 根据提示词+垫图生成图;\n"
        help_text += "/up 任务ID 序号执行动作;\n"
        help_text += "/describe 图片转文字;\n"
        help_text += "/shorten 提示词分析;\n"
        return help_text
