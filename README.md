## 文件说明

- iat_ws_python3.py  文件为科大讯飞官方demo文件
- voice2text.py  文件调用科大讯飞语音听写流式 WebAPI 接口实现语音转文字功能。
- tools.py  文件封装大模型function_calling功能，输入接口为模型名称、tools、functions_list。具体暂时仅仅使用本地python解释器功能（存在调用失败现象，具体原因未知）
- test.py  文件为测试文件，写了一点few_shot功能，目前仅在glm4上测试过，能够分析一定态势情况，但是相应数据不太准确，需进一步修改simulation_output_dictionary.md  说明文件，以及few_shot中的QA问题。个人感觉可能是不应该将草原物种分为生物和Agent两类 or QA环节虚拟数据对后续大模型回答产生一定的影响。


注：function calling功能的实现可以使用最新开源的LangChain模块完成，涉及到多智能体、多终端则使用LangGraph实现。  其功能相对来说比较完善，易完成。