# wechat-ai
基于 [chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat) 和 [midjourney-proxy](https://github.com/novicezk/midjourney-proxy)3.x开发的微信智能机器人

# 主要功能

- [x] 支持[chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat)的全功能
- [x] 支持MJ的Imagine操作
- [x] 支持MJ的Zoom(图片变焦)、Pan(焦点移动) 等功能
- [x] 支持MJ的Describe(图生文) 指令和相关动作
- [x] 支持MJ的Shorten 指令和相关动作

# 后续计划

- [ ] 支持MJ的Blend(图片混合) 指令和相关动作
- [ ] 支持MJ的所有remix模型下的操作
- [ ] 基于langchain的知识库功能
- [ ] 用户使用次数控制
- [ ] 后台管理界面
- [ ] ...

# 使用示例

①GPT对话

<img src="https://raw.githubusercontent.com/litter-coder/wechat-ai/main/docs/images/chat.png" alt="GPT对话"/>

②查看功能

<img src="https://raw.githubusercontent.com/litter-coder/wechat-ai/main/docs/images/help.png" alt="查看功能"/>

③MJ绘图

<img src="https://raw.githubusercontent.com/litter-coder/wechat-ai/main/docs/images/imagine.png" alt="MJ绘图"/>

④MJ操作

<img src="https://raw.githubusercontent.com/litter-coder/wechat-ai/main/docs/images/up.png" alt="MJ操作"/>

# 部署方式

## 1.运行环境

支持 Linux、MacOS、Windows 系统（可在Linux服务器上长期运行)，同时需安装 `Python`。

> 建议Python版本在 3.7.1~3.9.X 之间，推荐3.8版本，3.10及以上版本在 MacOS 可用，其他系统上不确定能否正常运行。

**(1) 克隆项目代码：**

```bash
git clone https://github.com/litter-coder/wechat-ai
cd wechat-ai/
```

**(2) 安装核心依赖 ：**

```bash
pip3 install -r requirements-optional.txt
```

## 2.配置

配置文件的模板在根目录的`config-template.json`中，需复制该模板创建最终生效的 `config.json` 文件：

```
  cp config-template.json config.json
```

然后在`config.json`中填入配置，以下是对默认配置的说明，可根据需要进行自定义修改（请去掉注释）：

```shell
# config.json文件内容示例
{
  "open_ai_api_key": "YOUR API KEY",          # 填入OpenAI API KEY
  "model": "gpt-3.5-turbo",                   # 模型名称
  "proxy": "",                                # 模型名称(海外服务器不需要填写)
  "single_chat_prefix": [""],                 # 私聊时文本需要包含该前缀才能触发机器人回复（为空则表示私聊都会触发）
  "single_chat_reply_prefix": "",             # 私聊时自动回复的前缀，用于区分真人（为空则表示不加前缀）
  "group_chat_prefix": ["@gpt"],              # 群聊时包含该前缀则会触发机器人回复
  "group_name_white_list": ["ALL_GROUP"],     # 开启自动回复的群名称列表（ALL_GROUP为所有群）
  "group_chat_in_one_session": ["ALL_GROUP"], # 支持会话上下文共享的群名称ALL_GROUP为所有群）  
  "image_create_prefix": [                    # 开启图片回复的前缀
    "画",
    "看",
    "找"
  ],
  "conversation_max_tokens": 1000,            # 开启图片回复的前缀
  "character_desc": "你是Piety Ai, 一个由LitterCoder训练的大型语言模型, 你旨在回答并解决人们的任何问题，并且可以使用多种语言与人交流。",
  "hot_reload": true,                         # 重启免登录配置
  "proxy_server": "http://127.0.0.1:8080/mj", # mj代理server配置
  "proxy_api_secret": ""                      # mj代理api密钥配置（没有可不配）
}
```

## 3.运行

### 1.本地运行

如果是开发机 **本地运行**，直接在项目根目录下执行：

```shell
python3 app.py
```

终端输出二维码后，使用微信进行扫码，当输出 "Start auto replying" 时表示自动回复程序已经成功运行了（注意：用于登录的微信需要在支付处已完成实名认证）。扫码登录后你的账号就成为机器人了，可以在微信手机端通过配置的关键词触发自动回复 (任意好友发送消息给你，或是自己发消息给好友)

### 2.服务器部署

使用nohup命令在后台运行程序：

```
nohup python3 app.py > out.log 2>&1 & tail -f out.log      
# 在后台运行程序并通过日志输出二维码
```

## 4.其他

### 1.查看进程

```shell
ps -ef | grep app.py
```

### 2.结束进程

```sh
kill -9 [进程id]
```

<img src="https://raw.githubusercontent.com/litter-coder/wechat-ai/main/docs/images/kill.png" alt="其他操作"/>

# 联系我们

问题咨询和商务合作可联系

 <img src="https://raw.githubusercontent.com/litter-coder/midjourney-proxy-plus/main/docs/manager-qrcode.jpeg" width="240" alt="微信二维码"/>

