# -*- coding:utf-8 -*-
#
#   author: iflytek
#
#  本demo测试时运行的环境为：Windows + Python3.7
#  本demo测试成功运行时所安装的第三方库及其版本如下，您可自行逐一或者复制到一个新的txt文件利用pip一次性安装：
#   cffi==1.12.3
#   gevent==1.4.0
#   greenlet==0.4.15
#   pycparser==2.19
#   six==1.12.0
#   websocket==0.2.1
#   websocket-client==0.56.0
#
#  语音听写流式 WebAPI 接口调用示例 接口文档（必看）：https://doc.xfyun.cn/rest_api/语音听写（流式版）.html
#  webapi 听写服务参考帖子（必看）：http://bbs.xfyun.cn/forum.php?mod=viewthread&tid=38947&extra=
#  语音听写流式WebAPI 服务，热词使用方式：登陆开放平台https://www.xfyun.cn/后，找到控制台--我的应用---语音听写（流式）---服务管理--个性化热词，
#  设置热词
#  注意：热词只能在识别的时候会增加热词的识别权重，需要注意的是增加相应词条的识别率，但并不是绝对的，具体效果以您测试为准。
#  语音听写流式WebAPI 服务，方言试用方法：登陆开放平台https://www.xfyun.cn/后，找到控制台--我的应用---语音听写（流式）---服务管理--识别语种列表
#  可添加语种或方言，添加后会显示该方言的参数值
#  错误码链接：https://www.xfyun.cn/document/error-code （code返回错误码时必看）
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import websocket
import datetime
import hashlib
import base64
import hmac
import json
import pyaudio
from urllib.parse import urlencode
import time
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import logging
from ws4py.client.threadedclient import WebSocketClient
import audioop

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class WsParam(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, AudioFile=None):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}

        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {
            "domain": "iat",
            "language": "zh_cn",
            "accent": "mandarin",
            "vinfo": 1,
            "vad_eos": 1000,
        }

    # 生成url
    def create_url(self):
        url = "wss://ws-api.xfyun.cn/v2/iat"
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(
            self.APISecret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = (
            'api_key="%s", algorithm="%s", headers="%s", signature="%s"'
            % (self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )
        # 将请求的鉴权参数组合为字典
        v = {"authorization": authorization, "date": date, "host": "ws-api.xfyun.cn"}
        # 拼接鉴权参数，生成url
        url = url + "?" + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url


class RecognitionWebsocket(WebSocketClient):
    def __init__(self, url, ws_param):
        super().__init__(url)
        self.ws_param = ws_param
        self.rec_text = {}

    def received_message(self, message):
        message = message.__str__()
        try:
            code = json.loads(message)["code"]
            sid = json.loads(message)["sid"]
            # status = json.loads(message)['data']['status']
            if code != 0:
                err_msg = json.loads(message)["message"]
                logging.warning(
                    "sid:%s call error:%s code is:%s" % (sid, err_msg, code)
                )
            else:
                data = json.loads(message)["data"]["result"]
                ws = data["ws"]
                sn = data["sn"]
                result = ""
                for i in ws:
                    for w in i["cw"]:
                        result += w["w"]
                self.rec_text[sn] = result
                logging.info("识别结果为: {}".format(self.rec_text))
        except Exception as e:
            logging.info(message)
            logging.error("receive msg,but parse exception: {}".format(e))

    def on_error(self, error):
        logging.error("### error: {}".format(error))

    def closed(self, code, reason=None):
        logging.info("语音识别通道关闭" + str(code) + str(reason))

    def opened(self):
        def run(*args):
            status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧
            CHUNK = 520  # 定义数据流块
            FORMAT = pyaudio.paInt16  # 16bit编码格式
            CHANNELS = 1  # 单声道
            RATE = 16000  # 16000采样频率
            threshold = 650  # 音量阈值
            interval = 0.04  # 发送音频间隔(单位:s)
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )

            num_silent = 0
            max_num_silent = 80
            while True:
                buf = stream.read(CHUNK)
                # 是否为空
                if not buf:
                    status = STATUS_LAST_FRAME

                # 静音判断
                # 计算音量
                rms = audioop.rms(buf, 2)
                # print("num_silent:%d  ,rms:%d ", num_silent, rms)
                if rms < threshold:
                    num_silent += 1
                    if num_silent > max_num_silent:
                        status = STATUS_LAST_FRAME
                else:
                    num_silent = 0

                if status == STATUS_FIRST_FRAME:
                    d = {
                        "common": self.ws_param.CommonArgs,
                        "business": self.ws_param.BusinessArgs,
                        "data": {
                            "status": 0,
                            "format": "audio/L16;rate=16000",
                            "audio": str(base64.b64encode(buf), "utf-8"),
                            "encoding": "raw",
                        },
                    }
                    d = json.dumps(d)
                    self.send(d)
                    status = STATUS_CONTINUE_FRAME
                elif status == STATUS_CONTINUE_FRAME:
                    d = {
                        "data": {
                            "status": 1,
                            "format": "audio/L16;rate=16000",
                            "audio": str(base64.b64encode(buf), "utf-8"),
                            "encoding": "raw",
                        }
                    }
                    d = json.dumps(d)
                    self.send(d)
                elif status == STATUS_LAST_FRAME:
                    d = {
                        "data": {
                            "status": 2,
                            "format": "audio/L16;rate=16000",
                            "audio": str(base64.b64encode(buf), "utf-8"),
                            "encoding": "raw",
                        }
                    }
                    d = json.dumps(d)
                    self.send(d)
                    logging.info("录音结束")
                    time.sleep(0.3)
                    stream.stop_stream()
                    stream.close()
                    audio.terminate()
                    break
                time.sleep(interval)
            self.close(1000, "")

        thread.start_new_thread(run, ())


def get_voice2text():
    wsParam = WsParam(
        APPID="83db5cc8",
        APISecret="MTdhMDJkMjgxMGM3ZGQ2NTViNTMzNmU0",
        APIKey="fc2fbe5181a76cc0b4c412bb97e5c36d",
    )

    ws_url = wsParam.create_url()
    ws = RecognitionWebsocket(ws_url, wsParam)
    ws.rec_text = {}
    ws.connect()
    ws.run_forever()
    # sorted_text = sorted(ws.rec_text.items())  # 按照键排序
    results = "".join([item[1] for item in ws.rec_text.items()])  # 连接字符串
    return results


# 用作语音测试
# if __name__ == "__main__":
#     wsParam = WsParam(
#         APPID="83db5cc8",
#         APISecret="MTdhMDJkMjgxMGM3ZGQ2NTViNTMzNmU0",
#         APIKey="fc2fbe5181a76cc0b4c412bb97e5c36d",
#         AudioFile=r"/home/yjq/rtasr_python3_demo/python/test_1.pcm",
#     )

#     ws_url = wsParam.create_url()
#     ws = RecognitionWebsocket(ws_url, wsParam)
#     ws.connect()
#     ws.run_forever()
#     sorted_text = sorted(ws.rec_text.items())  # 按照键排序
#     results = "".join([item[1] for item in sorted_text])  # 连接字符串
#     print(results)
