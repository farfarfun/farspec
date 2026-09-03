# farspec

`farspec` 是一个纯 Python 的任务协议规范包：提供 `Request`/`Response`/`Task` 基类，
以及 dataclass ↔ dict（JSON 友好）的通用序列化工具，方便在不同服务/任务系统之间
约定统一的输入输出结构。不依赖网络、数据库或云服务。

## 特性

- `BaseRequest`：请求基类，自动生成 `request_id`，`meta` 承载版本/追踪等横切信息
- `BaseResponse`：响应基类，内置 `status`/`events`/耗时统计与成功/失败标记方法
- `BaseTask`：模板方法基类，`run()` 统一处理开始/结束时间戳、事件记录与异常捕获
- `to_jsonable`/`from_jsonable`/`dataclass_to_dict`/`dataclass_from_dict`：通用的
  dataclass ↔ JSON 友好 dict 转换工具，支持 `X | None`、`list`、`dict`、`Enum`、
  `datetime`、嵌套 dataclass

## 环境要求

- Python 3.10 或更高版本

## 安装

```bash
pip install farspec
```

## 快速开始

```python
from farspec.task import BaseRequest, BaseResponse, BaseTask


class EchoTask(BaseTask[BaseRequest, BaseResponse]):
    def build_response(self) -> BaseResponse:
        return BaseResponse()

    def execute(self, response: BaseResponse, *args, **kwargs) -> BaseResponse:
        response.add_event("echo", "doing work")
        response.mark_succeeded(payload={"echoed": True})
        return response


task = EchoTask(BaseRequest(request_id="req-42"))
result = task.run()

print(result.status)   # TaskStatus.SUCCEEDED
print(result.payload)  # {'echoed': True}
print(result.to_dict())  # JSON 友好 dict，可直接 json.dumps
```

## 开发

```bash
uv sync
python -m pytest tests/ -v
```

## 许可证

本项目使用 [MIT License](LICENSE)。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
