# Observability 模块设计文档

## 1. 模块概述

### 1.1 模块名称

Observability（可观测性模块）

### 1.2 职责

Observability 模块是 Mozi AI Coding Agent 的横切面可观测性组件，负责：
- 提供统一结构化日志系统
- 定义和采集关键 Metrics 指标
- 实现分布式链路追踪
- 支持运行时诊断和性能分析
- 提供审计追溯能力

### 1.3 核心能力

| 能力 | 说明 |
| ---- | ---- |
| 结构化日志 | JSON 格式日志、多级别输出、上下文关联 |
| Metrics 指标 | Counter/Gauge/Histogram/Timer 指标类型 |
| 链路追踪 | Trace ID 传递、Span 生成、调用链可视化 |
| 性能分析 | 关键操作耗时统计、资源使用监控 |
| 审计日志 | 操作记录、安全事件追溯 |

### 1.4 核心问题

| 问题 | 说明 |
| ---- | ---- |
| 日志分散 | 各模块独立日志，缺乏统一格式和聚合 |
| 性能诊断难 | 无法追踪请求在系统中的完整调用链 |
| 指标缺失 | 缺乏关键业务指标，难以评估系统状态 |
| 问题定位 | 出现问题时难以快速定位根本原因 |

### 1.5 难点

| 难点 | 说明 |
| ---- | ---- |
| 零侵入设计 | 如何在不修改业务代码的情况下添加可观测性 |
| 性能开销 | 日志、追踪、指标采集对系统性能的影响 |
| 上下文传递 | Trace ID 如何在异步调用链中传递 |
| 存储成本 | 大量日志和追踪数据的存储问题 |

### 1.6 解决方案

| 方案 | 说明 |
| ---- | ---- |
| 结构化日志 | JSON 格式日志，包含 trace_id、session_id 等上下文 |
| 链路追踪 | Span 机制，支持分布式追踪 |
| Metrics 聚合 | Counter/Gauge/Histogram 指标类型 |
| OTLP 导出 | 支持 OpenTelemetry 协议导出到外部系统 |

---

## 2. 模块结构

### 2.1 目录结构

```
mozi/observability/
    __init__.py                 # 模块导出
    logger.py                   # 结构化日志器
    metrics.py                  # Metrics 指标定义
    tracer.py                   # 链路追踪器
    context.py                  # 可观测性上下文
    exporter.py                 # 数据导出器（Console/JSON/OTLP）
    service.py                  # 统一可观测性服务
```

### 2.2 关键文件说明

| 文件 | 职责 |
| ---- | ---- |
| logger.py | 结构化日志器，提供 log()、debug()、info()、warn()、error() 等方法 |
| metrics.py | 定义指标类型和采集接口 |
| tracer.py | Trace/Span 管理，Context 传播 |
| context.py | 可观测性上下文（Trace ID、Span ID 等） |
| exporter.py | 日志和指标的导出器，支持多种输出格式 |
| service.py | 统一封装，对外提供简洁接口 |

---

## 3. 结构化日志

### 3.1 日志格式

Mozi 采用 JSON 格式结构化日志，确保日志可解析、可搜索：

```json
{
    "timestamp": "2026-03-29T10:30:00.000Z",
    "level": "INFO",
    "message": "Tool executed successfully",
    "trace_id": "abc123-def456-ghi789",
    "span_id": "span-001",
    "module": "tools",
    "function": "execute_tool",
    "session_id": "sess-xxx",
    "user_id": "user-yyy",
    "duration_ms": 45,
    "metadata": {
        "tool_name": "read_file",
        "file_path": "/Users/lijunyi/road/mozi/README.md",
        "status": "success"
    }
}
```

### 3.2 日志字段定义

| 字段 | 类型 | 必填 | 说明 |
| ---- | ---- | ---- | ---- |
| timestamp | string | 是 | ISO 8601 格式时间戳 |
| level | string | 是 | DEBUG/INFO/WARN/ERROR |
| message | string | 是 | 日志消息 |
| trace_id | string | 否 | 链路追踪 ID |
| span_id | string | 否 | 当前 Span ID |
| module | string | 是 | 模块名称 |
| function | string | 是 | 函数名称 |
| session_id | string | 否 | 会话 ID |
| user_id | string | 否 | 用户 ID |
| duration_ms | number | 否 | 操作耗时（毫秒） |
| metadata | object | 否 | 额外元数据 |

### 3.3 日志级别

| 级别 | 使用场景 |
| ---- | -------- |
| DEBUG | 详细调试信息，参数值、返回值 |
| INFO | 正常业务流程：任务开始/结束、工具执行 |
| WARN | 潜在问题：重试、fallback、配置缺失 |
| ERROR | 操作失败：工具执行失败、API 错误 |
| CRITICAL | 系统级错误：认证失败、安全违规 |

### 3.4 日志输出配置

```python
class LogExporter:
    """日志导出器"""

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        format: LogFormat = LogFormat.JSON,
        output: LogOutput = LogOutput.CONSOLE,
    ) -> None:
        self._level = level
        self._format = format
        self._output = output

    def export(self, record: LogRecord) -> None:
        """导出日志记录"""
        if record.level < self._level:
            return

        if self._format == LogFormat.JSON:
            self._export_json(record)
        elif self._format == LogFormat.PLAINTEXT:
            self._export_plaintext(record)

    def _export_json(self, record: LogRecord) -> None:
        """JSON 格式导出"""
        import json
        output = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "trace_id": record.trace_id,
            "span_id": record.span_id,
            "module": record.module,
            "function": record.function,
            "session_id": record.session_id,
            "user_id": record.user_id,
            "duration_ms": record.duration_ms,
            "metadata": record.metadata,
        }
        json.dump(output, self._output, default=str)

    def _export_plaintext(self, record: LogRecord) -> None:
        """纯文本格式导出（用于开发调试）"""
        ts = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{ts} [{record.level.name}] {record.module}.{record.function}: {record.message}")
```

### 3.5 日志器接口

```python
class StructuredLogger:
    """结构化日志器"""

    def __init__(
        self,
        module: str,
        exporter: LogExporter,
        trace_context: TraceContext | None = None,
    ) -> None:
        self._module = module
        self._exporter = exporter
        self._trace_context = trace_context or TraceContext()

    def _log(
        self,
        level: LogLevel,
        message: str,
        **metadata: Any,
    ) -> None:
        """内部日志记录方法"""
        record = LogRecord(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            trace_id=self._trace_context.trace_id,
            span_id=self._trace_context.current_span_id,
            module=self._module,
            function=self._get_caller_function(),
            session_id=self._trace_context.session_id,
            user_id=self._trace_context.user_id,
            metadata=metadata,
        )
        self._exporter.export(record)

    def debug(self, message: str, **metadata: Any) -> None:
        """DEBUG 级别日志"""
        self._log(LogLevel.DEBUG, message, **metadata)

    def info(self, message: str, **metadata: Any) -> None:
        """INFO 级别日志"""
        self._log(LogLevel.INFO, message, **metadata)

    def warn(self, message: str, **metadata: Any) -> None:
        """WARN 级别日志"""
        self._log(LogLevel.WARN, message, **metadata)

    def error(self, message: str, **metadata: Any) -> None:
        """ERROR 级别日志"""
        self._log(LogLevel.ERROR, message, **metadata)

    def critical(self, message: str, **metadata: Any) -> None:
        """CRITICAL 级别日志"""
        self._log(LogLevel.CRITICAL, message, **metadata)

    def _get_caller_function(self) -> str:
        """获取调用者函数名"""
        import traceback
        stack = traceback.extract_stack()
        if len(stack) > 2:
            return stack[-3].name
        return "unknown"
```

---

## 4. Metrics 指标

### 4.1 指标类型

| 类型 | 说明 | 使用场景 |
| ---- | ---- | -------- |
| Counter | 递增计数器 | 请求次数、错误次数、任务完成数 |
| Gauge | 可变数值 | 当前队列深度、活跃连接数 |
| Histogram | 分布统计 | 请求耗时、文件大小分布 |
| Timer | 时间测量 | 操作耗时，自动记录 duration_ms |

### 4.2 核心指标定义

```python
class MetricsCollector:
    """指标采集器"""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._registry: list[str] = []

    def register_counter(
        self,
        name: str,
        description: str,
        labels: dict[str, str] | None = None,
    ) -> Counter:
        """注册计数器"""
        counter = Counter(
            name=name,
            description=description,
            labels=labels or {},
        )
        self._counters[name] = counter
        self._registry.append(name)
        return counter

    def register_gauge(
        self,
        name: str,
        description: str,
        labels: dict[str, str] | None = None,
    ) -> Gauge:
        """注册 Gauge"""
        gauge = Gauge(
            name=name,
            description=description,
            labels=labels or {},
        )
        self._gauges[name] = gauge
        self._registry.append(name)
        return gauge

    def register_histogram(
        self,
        name: str,
        description: str,
        buckets: list[float] | None = None,
        labels: dict[str, str] | None = None,
    ) -> Histogram:
        """注册直方图"""
        histogram = Histogram(
            name=name,
            description=description,
            buckets=buckets or DEFAULT_BUCKETS,
            labels=labels or {},
        )
        self._histograms[name] = histogram
        self._registry.append(name)
        return histogram

    def get_counter(self, name: str) -> Counter | None:
        """获取计数器"""
        return self._counters.get(name)

    def get_gauge(self, name: str) -> Gauge | None:
        """获取 Gauge"""
        return self._gauges.get(name)

    def get_histogram(self, name: str) -> Histogram | None:
        """获取直方图"""
        return self._histograms.get(name)


# 默认直方图桶（用于耗时统计）
DEFAULT_BUCKETS: list[float] = [
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
]
```

### 4.3 预定义指标

| 指标名称 | 类型 | 标签 | 说明 |
| -------- | ---- | ---- | ---- |
| mozi_requests_total | Counter | method, endpoint, status | HTTP 请求总数 |
| mozi_tasks_total | Counter | status | 任务执行总数 |
| mozi_tasks_duration_seconds | Histogram | complexity | 任务耗时分布 |
| mozi_tools_invocations_total | Counter | tool_name, status | 工具调用总数 |
| mozi_tools_duration_seconds | Histogram | tool_name | 工具执行耗时 |
| mozi_session_active | Gauge | - | 当前活跃会话数 |
| mozi_context_tokens | Histogram | - | Token 使用量分布 |
| mozi_model_calls_total | Counter | model, status | 模型调用总数 |
| mozi_model_duration_seconds | Histogram | model | 模型响应耗时 |
| mozi_errors_total | Counter | error_type, module | 错误总数 |

### 4.4 指标数据格式

```json
{
    "metric_name": "mozi_tasks_duration_seconds",
    "type": "histogram",
    "labels": {
        "complexity": "SIMPLE"
    },
    "buckets": {
        "0.005": 10,
        "0.01": 25,
        "0.025": 45,
        "0.05": 60,
        "0.1": 75,
        "0.25": 90,
        "0.5": 95,
        "1.0": 98,
        "2.5": 99,
        "5.0": 100,
        "10.0": 100
    },
    "sum": 45.678,
    "count": 100,
    "timestamp": "2026-03-29T10:30:00Z"
}
```

---

## 5. 链路追踪

### 5.1 追踪数据模型

```
Trace
├── Span 1 (root)
│   ├── Span 1.1 (orchestrator)
│   │   ├── Span 1.1.1 (intent_detection)
│   │   └── Span 1.1.2 (complexity_scoring)
│   └── Span 1.2 (context_building)
│       ├── Span 1.2.1 (memory_recall)
│       └── Span 1.2.2 (context_compile)
└── Span 2 (model_invocation)
    └── Span 2.1 (tools_execution)
        ├── Span 2.1.1 (read_file)
        └── Span 2.1.2 (bash)
```

### 5.2 Trace 上下文传播

Trace ID 和 Span ID 通过以下方式传播：

| 传播方式 | 说明 | 实现 |
| -------- | ---- | ---- |
| In-Process | 同一进程内传递 | ThreadLocal/ContextVar |
| Cross-Process | 进程间传递（如 MCP） | HTTP Header (traceparent) |
| Event-Driven | 事件总线传递 | Event Payload |

### 5.3 Span 接口定义

```python
@dataclass
class Span:
    """追踪跨度"""
    name: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    start_time: datetime
    end_time: datetime | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        """计算跨度耗时"""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        """设置属性"""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """添加跨度事件"""
        self.events.append(SpanEvent(
            name=name,
            timestamp=datetime.utcnow(),
            attributes=attributes or {},
        ))

    def set_status(self, status: SpanStatus) -> None:
        """设置状态"""
        self.status = status

    def finish(self) -> None:
        """结束跨度"""
        self.end_time = datetime.utcnow()


@dataclass
class SpanEvent:
    """跨度事件"""
    name: str
    timestamp: datetime
    attributes: dict[str, Any] = field(default_factory=dict)


class SpanStatus(Enum):
    """跨度状态"""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"
```

### 5.4 链路追踪器接口

```python
class Tracer:
    """链路追踪器"""

    def __init__(self, service_name: str = "mozi") -> None:
        self._service_name = service_name
        self._current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
            "current_span", default=None
        )
        self._spans: dict[str, list[Span]] = {}

    @property
    def current_span(self) -> Span | None:
        """获取当前跨度"""
        return self._current_span.get()

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """启动新跨度"""
        import uuid

        span_id = f"span-{uuid.uuid4().hex[:16]}"
        trace_id = trace_id or self._generate_trace_id()

        parent_span = self.current_span
        if parent_span_id is None and parent_span is not None:
            parent_span_id = parent_span.span_id

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            start_time=datetime.utcnow(),
            attributes=attributes or {},
        )

        self._current_span.set(span)

        if trace_id not in self._spans:
            self._spans[trace_id] = []
        self._spans[trace_id].append(span)

        return span

    def end_span(self, span: Span) -> None:
        """结束跨度"""
        span.finish()
        self._current_span.set(None)

    def get_trace(self, trace_id: str) -> list[Span]:
        """获取完整追踪链"""
        return self._spans.get(trace_id, [])

    def _generate_trace_id(self) -> str:
        """生成追踪 ID"""
        import uuid
        return uuid.uuid4().hex

    def inject_context(self, carrier: dict[str, str]) -> dict[str, str]:
        """注入追踪上下文到载体（如 HTTP Header）"""
        span = self.current_span
        if span is not None:
            carrier["traceparent"] = f"00-{span.trace_id}-{span.span_id}-01"
        return carrier

    def extract_context(self, carrier: dict[str, str]) -> str | None:
        """从载体提取追踪上下文"""
        traceparent = carrier.get("traceparent")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 2:
                return parts[1]
        return None


class TraceContext:
    """追踪上下文管理器（用于 with 语句）"""

    def __init__(
        self,
        tracer: Tracer,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self._tracer = tracer
        self._name = name
        self._attributes = attributes
        self._span: Span | None = None

    def __enter__(self) -> Span:
        """进入上下文"""
        self._span = self._tracer.start_span(
            name=self._name,
            attributes=self._attributes,
        )
        return self._span

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """退出上下文"""
        if self._span is not None:
            if exc_type is not None:
                self._span.set_status(SpanStatus.ERROR)
                self._span.set_attribute("error.type", exc_type.__name__)
                self._span.set_attribute("error.message", str(exc_val))
            self._tracer.end_span(self._span)
```

---

## 6. 接口设计

### 6.1 核心类型定义

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import contextvars


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """日志格式"""
    JSON = "json"
    PLAINTEXT = "plaintext"


class LogOutput(Enum):
    """日志输出"""
    CONSOLE = "console"
    FILE = "file"
    STDERR = "stderr"


@dataclass
class LogRecord:
    """日志记录"""
    timestamp: datetime
    level: LogLevel
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    module: str = ""
    function: str = ""
    session_id: str | None = None
    user_id: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Counter:
    """计数器指标"""
    name: str
    description: str
    labels: dict[str, str]
    value: float = 0.0

    def increment(self, value: float = 1.0) -> None:
        """递增"""
        self.value += value


@dataclass
class Gauge:
    """可变数值指标"""
    name: str
    description: str
    labels: dict[str, str]
    value: float = 0.0

    def set(self, value: float) -> None:
        """设置值"""
        self.value = value

    def inc(self) -> None:
        """递增"""
        self.value += 1

    def dec(self) -> None:
        """递减"""
        self.value -= 1


@dataclass
class Histogram:
    """直方图指标"""
    name: str
    description: str
    labels: dict[str, str]
    buckets: list[float]
    sum: float = 0.0
    count: int = 0
    bucket_counts: dict[float, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化桶计数"""
        self.bucket_counts = {b: 0 for b in self.buckets}

    def observe(self, value: float) -> None:
        """记录观测值"""
        self.sum += value
        self.count += 1
        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1


@dataclass
class Timer:
    """计时器指标（自动记录耗时）"""

    def __init__(
        self,
        histogram: Histogram,
        start_time: datetime | None = None,
    ) -> None:
        self._histogram = histogram
        self._start_time = start_time or datetime.utcnow()

    def stop(self) -> float:
        """停止计时并记录"""
        import time
        duration = (datetime.utcnow() - self._start_time).total_seconds()
        self._histogram.observe(duration)
        return duration
```

### 6.2 ObservabilityService 接口

```python
class ObservabilityService:
    """统一可观测性服务"""

    def __init__(
        self,
        service_name: str = "mozi",
        log_level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.JSON,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
    ) -> None:
        self._service_name = service_name
        self._tracer = Tracer(service_name) if enable_tracing else None
        self._metrics = MetricsCollector() if enable_metrics else None
        self._logger_exporter = LogExporter(
            level=log_level,
            format=log_format,
            output=LogOutput.CONSOLE,
        )
        self._init_default_metrics()

    def _init_default_metrics(self) -> None:
        """初始化默认指标"""
        if self._metrics is None:
            return

        self._metrics.register_counter(
            "mozi_requests_total",
            "Total number of requests",
        )
        self._metrics.register_counter(
            "mozi_tasks_total",
            "Total number of tasks",
        )
        self._metrics.register_histogram(
            "mozi_tasks_duration_seconds",
            "Task duration distribution",
        )
        self._metrics.register_counter(
            "mozi_tools_invocations_total",
            "Total tool invocations",
        )
        self._metrics.register_histogram(
            "mozi_tools_duration_seconds",
            "Tool invocation duration",
        )
        self._metrics.register_gauge(
            "mozi_session_active",
            "Number of active sessions",
        )

    def get_logger(self, module: str) -> StructuredLogger:
        """获取模块日志器"""
        return StructuredLogger(
            module=module,
            exporter=self._logger_exporter,
            trace_context=TraceContext(
                tracer=self._tracer,
                trace_id=None,
                span_id=None,
            ) if self._tracer else None,
        )

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Span | None:
        """启动追踪跨度"""
        if self._tracer is None:
            return None
        return self._tracer.start_span(name=name, attributes=attributes)

    def get_tracer(self) -> Tracer | None:
        """获取追踪器"""
        return self._tracer

    def get_metrics(self) -> MetricsCollector | None:
        """获取指标采集器"""
        return self._metrics

    def record_task_duration(self, duration: float, complexity: str) -> None:
        """记录任务耗时"""
        if self._metrics is None:
            return
        histogram = self._metrics.get_histogram("mozi_tasks_duration_seconds")
        if histogram is not None:
            histogram.labels["complexity"] = complexity
            histogram.observe(duration)

    def record_tool_invocation(
        self,
        tool_name: str,
        status: str,
        duration: float,
    ) -> None:
        """记录工具调用"""
        if self._metrics is None:
            return
        counter = self._metrics.get_counter("mozi_tools_invocations_total")
        if counter is not None:
            counter.labels["tool_name"] = tool_name
            counter.labels["status"] = status
            counter.increment()

        histogram = self._metrics.get_histogram("mozi_tools_duration_seconds")
        if histogram is not None:
            histogram.labels["tool_name"] = tool_name
            histogram.observe(duration)

    def increment_error(self, error_type: str, module: str) -> None:
        """记录错误"""
        if self._metrics is None:
            return
        counter = self._metrics.get_counter("mozi_errors_total")
        if counter is not None:
            counter.labels["error_type"] = error_type
            counter.labels["module"] = module
            counter.increment()
```

### 6.3 全局可观测性管理器

```python
_observability_service: contextvars.ContextVar[ObservabilityService | None] = (
    contextvars.ContextVar("observability_service", default=None)
)


def get_observability() -> ObservabilityService:
    """获取全局可观测性服务"""
    service = _observability_service.get()
    if service is None:
        service = ObservabilityService()
        _observability_service.set(service)
    return service


def set_observability(service: ObservabilityService) -> None:
    """设置全局可观测性服务"""
    _observability_service.set(service)


def get_logger(module: str) -> StructuredLogger:
    """获取模块日志器的便捷函数"""
    return get_observability().get_logger(module)
```

---

## 7. 数据流

### 7.1 与各模块的交互关系

```
┌─────────────────────────────────────────────────────────┐
│                      Ingress Layer                        │
│                   CLI / MCP Client                       │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Orchestrator Layer                      │
│         Intent │ Complexity │ Routing                    │
└─────────────────────────┬───────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Tools     │  │    Model     │  │   Memory      │
│   Module     │  │   Module     │  │   Module      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Observability Module                        │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  │
│  │ Logger  │  │ Metrics  │  │ Tracer  │  │ Exporter │  │
│  │         │  │Collector  │  │         │  │          │  │
│  └─────────┘  └──────────┘  └─────────┘  └──────────┘  │
└─────────────────────────┬───────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                      │
│              Storage │ EventBus │ Config                  │
└─────────────────────────────────────────────────────────┘
```

### 7.2 日志数据流

```
1. 模块调用 get_logger("tools")
       │
       ▼
2. ObservabilityService 返回 StructuredLogger
       │
       ▼
3. 模块执行操作，调用 logger.info("message", **metadata)
       │
       ▼
4. StructuredLogger._log() 构建 LogRecord
       │
       ▼
5. LogRecord 通过 LogExporter.export() 输出
       │
       ▼
6. Console/JSON File/OTLP Endpoint
```

### 7.3 追踪数据流

```
1. 请求进入 Ingress
       │
       ▼
2. Tracer.start_span("ingress") 创建根 Span
       │
       ▼
3. Trace ID 存入 TraceContext
       │
       ▼
4. 传播到 Orchestrator（start_span 嵌套）
       │
       ▼
5. EventBus 携带 trace_id 发布事件
       │
       ▼
6. Tools/Model/Memory 执行，生成子 Span
       │
       ▼
7. Span.finish() 记录 end_time
       │
       ▼
8. Exporter 收集完整 Trace 输出
```

### 7.4 指标数据流

```
1. MetricsCollector.register_*() 注册指标
       │
       ▼
2. 操作触发 record_*() 方法
       │
       ▼
3. Counter/Gauge/Histogram 更新
       │
       ▼
4. Prometheus/JSON Exporter 定时采集
       │
       ▼
5. 输出到监控系统或日志
```

---

## 8. 错误处理

> **统一错误处理**：本模块的错误处理遵循统一异常体系，详细规范见 [error_handling.md](./2026-03-29_error_handling.md)。

---

## 9. 测试策略

### 9.1 测试结构

```
tests/unit/observability/
    __init__.py
    test_logger.py              # StructuredLogger 测试
    test_metrics.py             # MetricsCollector 测试
    test_tracer.py              # Tracer 测试
    test_span.py                # Span 测试
    test_exporter.py            # LogExporter 测试
    test_service.py             # ObservabilityService 测试
```

### 9.2 测试覆盖要求

| 组件 | 覆盖率目标 |
| ---- | --------- |
| logger.py | >= 90% |
| metrics.py | >= 90% |
| tracer.py | >= 90% |
| exporter.py | >= 85% |
| service.py | >= 85% |
| 整体模块 | >= 80% |

### 9.3 测试用例要求

**必须覆盖：**

| 测试场景 | 说明 |
| -------- | ---- |
| 日志级别过滤 | DEBUG 级别在 INFO 级别时不输出 |
| JSON 格式输出 | 验证 JSON 结构完整性 |
| 追踪 ID 传播 | 父子 Span 共享同一 trace_id |
| Span 嵌套 | 多层嵌套 Span 的父子关系 |
| Counter 递增 | 多次递增后数值正确 |
| Histogram 桶分布 | 观测值落入正确桶 |
| Gauge 增减 | set/inc/dec 操作正确 |
| 导出器降级 | 主导出器失败时切换到 fallback |

**测试示例：**

```python
import pytest
from datetime import datetime


@pytest.mark.unit
class TestStructuredLogger:
    def test_log_level_filter(self):
        """测试日志级别过滤"""
        records = []
        exporter = TestLogExporter(records)
        logger = StructuredLogger("test", exporter)

        logger.set_level(LogLevel.INFO)
        logger.debug("debug message")  # 应该被过滤
        logger.info("info message")

        assert len(records) == 1
        assert records[0].message == "info message"

    def test_json_format(self):
        """测试 JSON 格式输出"""
        records = []
        exporter = TestLogExporter(records, format=LogFormat.JSON)
        logger = StructuredLogger("test", exporter)

        logger.info("test message", foo="bar")

        assert len(records) == 1
        assert records[0].level == LogLevel.INFO
        assert records[0].metadata["foo"] == "bar"


@pytest.mark.unit
class TestTracer:
    def test_trace_id_propagation(self):
        """测试追踪 ID 传播"""
        tracer = Tracer("test")
        parent = tracer.start_span("parent")

        assert parent.trace_id is not None
        assert parent.span_id is not None

        child = tracer.start_span("child")

        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id

    def test_span_duration(self):
        """测试跨度耗时计算"""
        tracer = Tracer("test")
        span = tracer.start_span("test")

        import time
        time.sleep(0.01)

        span.finish()

        assert span.duration_ms is not None
        assert span.duration_ms >= 10

    def test_nested_spans(self):
        """测试嵌套跨度"""
        tracer = Tracer("test")
        spans = []

        with tracer.span("outer") as s1:
            spans.append(s1)
            with tracer.span("middle") as s2:
                spans.append(s2)
                with tracer.span("inner") as s3:
                    spans.append(s3)

        assert len(spans) == 3
        assert spans[0].span_id == spans[1].parent_span_id
        assert spans[1].span_id == spans[2].parent_span_id


@pytest.mark.unit
class TestMetricsCollector:
    def test_counter_increment(self):
        """测试计数器递增"""
        collector = MetricsCollector()
        counter = collector.register_counter(
            "test_counter",
            "Test counter",
        )

        counter.increment()
        counter.increment(5)

        assert counter.value == 6

    def test_histogram_observe(self):
        """测试直方图观测"""
        collector = MetricsCollector()
        histogram = collector.register_histogram(
            "test_histogram",
            "Test histogram",
            buckets=[0.1, 0.5, 1.0],
        )

        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)

        assert histogram.count == 3
        assert histogram.bucket_counts[0.1] == 1
        assert histogram.bucket_counts[0.5] == 2
        assert histogram.bucket_counts[1.0] == 3

    def test_gauge_set(self):
        """测试 Gauge 设置"""
        collector = MetricsCollector()
        gauge = collector.register_gauge(
            "test_gauge",
            "Test gauge",
        )

        gauge.set(10)
        assert gauge.value == 10

        gauge.inc()
        assert gauge.value == 11

        gauge.dec(3)
        assert gauge.value == 8


@pytest.mark.unit
class TestSpan:
    def test_set_attributes(self):
        """测试设置属性"""
        span = Span(
            name="test",
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id=None,
            start_time=datetime.utcnow(),
        )

        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 123)

        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == 123

    def test_add_event(self):
        """测试添加事件"""
        span = Span(
            name="test",
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id=None,
            start_time=datetime.utcnow(),
        )

        span.add_event("event1", {"foo": "bar"})

        assert len(span.events) == 1
        assert span.events[0].name == "event1"
        assert span.events[0].attributes["foo"] == "bar"

    def test_error_status(self):
        """测试错误状态"""
        span = Span(
            name="test",
            trace_id="trace-1",
            span_id="span-1",
            parent_span_id=None,
            start_time=datetime.utcnow(),
        )

        span.set_status(SpanStatus.ERROR)
        span.set_attribute("error.type", "ValueError")

        assert span.status == SpanStatus.ERROR
        assert span.attributes["error.type"] == "ValueError"


class TestLogExporter:
    """测试导出器（用于单元测试）"""

    def __init__(
        self,
        records: list[LogRecord],
        level: LogLevel = LogLevel.DEBUG,
        format: LogFormat = LogFormat.JSON,
    ) -> None:
        self._records = records
        self._level = level
        self._format = format

    def export(self, record: LogRecord) -> None:
        """记录日志"""
        if record.level >= self._level:
            self._records.append(record)
```

---

## 10. 可观测性汇总

> **说明**：本章节汇总所有模块的可观测性（日志、指标）配置，便于统一管理和查阅。
> 各模块详细可观测性实现请参考本模块设计文档。
> 统一错误处理规范见 [error_handling.md](./2026-03-29_error_handling.md)。

### 10.1 各模块日志事件汇总

| 模块 | 事件名 | 级别 | 字段 | 说明 |
| ---- | ------ | ---- | ---- | ---- |
| **Orchestrator** | `orchestrator_start` | INFO | `task_id`, `complexity` | 编排器开始处理 |
| | `orchestrator_end` | INFO | `task_id`, `duration_ms`, `status` | 编排器处理完成 |
| | `agent_selected` | DEBUG | `task_id`, `agent_type`, `agent_id` | Agent 选择结果 |
| | `routing_decision` | DEBUG | `task_id`, `complexity`, `route` | 路由决策 |
| | `intent_detected` | DEBUG | `task_id`, `intent_type`, `confidence` | 意图检测结果 |
| | `complexity_scored` | DEBUG | `task_id`, `score`, `level` | 复杂度评分 |
| **Task** | `task_created` | INFO | `task_id`, `parent_id`, `type` | 任务创建 |
| | `task_started` | INFO | `task_id`, `agent_id` | 任务开始执行 |
| | `task_completed` | INFO | `task_id`, `duration_ms` | 任务完成 |
| | `task_failed` | ERROR | `task_id`, `error`, `retry_count` | 任务失败 |
| | `task_retried` | WARN | `task_id`, `retry_count`, `max_retries` | 任务重试 |
| | `task_timeout` | WARN | `task_id`, `timeout_seconds` | 任务超时 |
| | `task_cancelled` | WARN | `task_id`, `reason` | 任务取消 |
| | `subtask_created` | DEBUG | `task_id`, `subtask_id`, `parent_id` | 子任务创建 |
| | `subtask_completed` | DEBUG | `subtask_id`, `parent_id` | 子任务完成 |
| | `rollback_initiated` | WARN | `task_id`, `reason` | 回滚启动 |
| | `rollback_completed` | INFO | `task_id`, `duration_ms` | 回滚完成 |
| | `circuit_breaker_open` | ERROR | `task_id`, `circuit_name` | 熔断器开启 |
| | `circuit_breaker_closed` | INFO | `circuit_name` | 熔断器关闭 |
| **Session** | `session_created` | INFO | `session_id`, `user_id`, `parent_session_id` | 会话创建 |
| | `session_updated` | DEBUG | `session_id`, `message_count`, `total_tokens` | 会话更新 |
| | `session_deleted` | INFO | `session_id` | 会话删除 |
| | `session_expired` | WARN | `session_id`, `age_days` | 会话过期 |
| | `storage_error` | ERROR | `session_id`, `operation`, `error` | 存储错误 |
| **Context** | `context_compaction` | INFO | `session_id`, `messages_in`, `messages_out` | 上下文压缩 |
| | `context_window_exceeded` | WARN | `session_id`, `token_count`, `max_tokens` | 上下文窗口超出 |
| | `message_truncated` | DEBUG | `session_id`, `original_length`, `truncated_length` | 消息截断 |
| **Memory** | `memory_stored` | DEBUG | `session_id`, `memory_id`, `type` | 记忆存储 |
| | `memory_retrieved` | DEBUG | `session_id`, `memory_id`, `relevance_score` | 记忆检索 |
| | `memory_forgotten` | DEBUG | `session_id`, `memory_id`, `reason` | 记忆遗忘 |
| | `memory_consolidated` | DEBUG | `session_id`, `memories_count` | 记忆整合 |
| | `retrieval_query` | DEBUG | `session_id`, `query_length`, `results_count` | 检索查询 |
| **Tools** | `tool_called` | INFO | `tool_name`, `session_id`, `arguments` | 工具调用 |
| | `tool_completed` | INFO | `tool_name`, `duration_ms`, `status` | 工具完成 |
| | `tool_failed` | ERROR | `tool_name`, `error`, `session_id` | 工具失败 |
| | `tool_timeout` | WARN | `tool_name`, `timeout_seconds` | 工具超时 |
| | `path_whitelist_violation` | WARN | `tool_name`, `path`, `session_id` | 路径白名单违规 |
| **Model** | `model_request` | INFO | `model`, `provider`, `input_tokens` | 模型请求 |
| | `model_response` | INFO | `model`, `provider`, `output_tokens`, `duration_ms` | 模型响应 |
| | `model_error` | ERROR | `model`, `provider`, `error` | 模型错误 |
| | `rate_limit_hit` | WARN | `model`, `provider`, `retry_after` | 速率限制 |
| | `token_limit_exceeded` | WARN | `model`, `max_tokens`, `requested_tokens` | Token 限制超出 |
| **Security** | `sandbox_created` | DEBUG | `session_id`, `sandbox_id` | 沙箱创建 |
| | `sandbox_command` | DEBUG | `sandbox_id`, `command` | 沙箱命令执行 |
| | `sandbox_violation` | WARN | `sandbox_id`, `violation_type`, `command` | 沙箱违规 |
| | `sandbox_closed` | DEBUG | `sandbox_id`, `duration_ms` | 沙箱关闭 |
| | `file_access_denied` | WARN | `session_id`, `file_path`, `reason` | 文件访问拒绝 |
| | `command_blocked` | WARN | `session_id`, `command`, `reason` | 命令阻断 |
| **Ingress/CLI** | `cli_started` | INFO | `version`, `user_id` | CLI 启动 |
| | `cli_command_received` | DEBUG | `command`, `args` | CLI 命令接收 |
| | `cli_session_start` | INFO | `session_id`, `user_id` | CLI 会话开始 |
| | `cli_session_end` | INFO | `session_id`, `duration_seconds` | CLI 会话结束 |
| | `repl_input` | DEBUG | `session_id`, `input_length` | REPL 输入 |
| | `repl_output` | DEBUG | `session_id`, `output_length` | REPL 输出 |
| | `output_ratelimited` | DEBUG | `session_id`, `limit_seconds` | 输出限流 |

### 10.2 各模块 Metrics 指标汇总

| 模块 | 指标名称 | 类型 | 标签 | 描述 |
| ---- | -------- | ---- | ---- | ---- |
| **Orchestrator** | `orchestrator_requests_total` | Counter | `status`, `complexity` | 编排器请求总数 |
| | `orchestrator_duration_seconds` | Histogram | `complexity`, `agent_type` | 编排器处理耗时 |
| | `orchestrator_routing_decisions_total` | Counter | `route`, `complexity` | 路由决策总数 |
| | `orchestrator_intent_detections_total` | Counter | `intent_type` | 意图检测总数 |
| **Task** | `tasks_total` | Counter | `status`, `type` | 任务执行总数 |
| | `tasks_duration_seconds` | Histogram | `complexity`, `type` | 任务执行耗时 |
| | `task_retries_total` | Counter | `task_type` | 任务重试总次数 |
| | `task_timeouts_total` | Counter | `task_type` | 任务超时总次数 |
| | `subtasks_total` | Counter | `status` | 子任务总数 |
| | `task_rollbacks_total` | Counter | `status` | 回滚总次数 |
| | `circuit_breaker_state` | Gauge | `circuit_name`, `state` | 熔断器状态 |
| **Session** | `session_created_total` | Counter | - | 创建的会话总数 |
| | `session_active` | Gauge | - | 当前活跃会话数 |
| | `session_messages_total` | Counter | - | 处理的的消息总数 |
| | `session_duration_seconds` | Histogram | - | 会话持续时间 |
| | `storage_operations_total` | Counter | `operation` | 存储操作总数 |
| | `storage_operation_duration` | Histogram | `operation` | 存储操作延迟 |
| **Context** | `context_compaction_total` | Counter | - | 上下文压缩总次数 |
| | `context_messages_in` | Histogram | - | 压缩前消息数 |
| | `context_messages_out` | Histogram | - | 压缩后消息数 |
| | `context_tokens` | Histogram | - | Token 使用量分布 |
| **Memory** | `memory_stored_total` | Counter | `memory_type` | 存储的记忆总数 |
| | `memory_retrieved_total` | Counter | `memory_type` | 检索的记忆总数 |
| | `memory_forgotten_total` | Counter | `reason` | 遗忘的记忆总数 |
| | `retrieval_latency_seconds` | Histogram | `retriever_type` | 检索延迟 |
| **Tools** | `tool_invocations_total` | Counter | `tool_name`, `status` | 工具调用总数 |
| | `tool_duration_seconds` | Histogram | `tool_name` | 工具执行耗时 |
| | `tool_errors_total` | Counter | `tool_name`, `error_type` | 工具错误总数 |
| | `path_violations_total` | Counter | `tool_name` | 路径违规总次数 |
| **Model** | `model_calls_total` | Counter | `model`, `provider`, `status` | 模型调用总数 |
| | `model_duration_seconds` | Histogram | `model`, `provider` | 模型响应耗时 |
| | `model_input_tokens` | Counter | `model`, `provider` | 输入 Token 总数 |
| | `model_output_tokens` | Counter | `model`, `provider` | 输出 Token 总数 |
| | `rate_limit_wait_seconds` | Histogram | `model`, `provider` | 速率限制等待时间 |
| **Security** | `sandbox_created_total` | Counter | - | 沙箱创建总数 |
| | `sandbox_violations_total` | Counter | `violation_type` | 沙箱违规总数 |
| | `sandbox_commands_total` | Counter | `status` | 沙箱命令总数 |
| | `file_access_denied_total` | Counter | `reason` | 文件访问拒绝次数 |
| | `command_blocked_total` | Counter | `reason` | 命令阻断总次数 |
| **Ingress/CLI** | `cli_sessions_total` | Counter | - | CLI 会话总数 |
| | `cli_active_sessions` | Gauge | - | 当前活跃 CLI 会话数 |
| | `cli_commands_total` | Counter | `command_type` | CLI 命令总数 |
| | `repl_inputs_total` | Counter | - | REPL 输入总次数 |
| | `output_ratelimit_hits_total` | Counter | - | 输出限流总次数 |

### 10.3 跨模块追踪 Span 设计

#### 10.3.1 完整调用链 Span 层次

```
Trace (trace_id)
├── Span: ingress (CLI/MCP 请求入口)
│   └── Span: orchestrator (编排层)
│       ├── Span: intent_detection (意图识别)
│       ├── Span: complexity_scoring (复杂度评估)
│       └── Span: routing (路由决策)
│       ├── Span: context_building (上下文构建)
│       │   ├── Span: memory_recall (记忆检索)
│       │   └── Span: context_compile (上下文编译)
│       ├── Span: agent_execution (Agent 执行)
│       │   └── Span: model_invocation (模型调用)
│       │       └── Span: tools_execution (工具执行)
│       │           ├── Span: tool_name (各工具调用)
│       │           └── Span: tool_result (工具结果处理)
│       └── Span: response_formation (响应生成)
└── Span: storage (存储操作)
    └── Span: session_save (会话保存)
```

#### 10.3.2 Span 属性规范

| Span 名称 | 必需属性 | 可选属性 |
| --------- | -------- | -------- |
| `ingress` | `session_id`, `request_type` | `user_id`, `cli_version` |
| `orchestrator` | `task_id`, `complexity` | `parent_task_id` |
| `intent_detection` | `intent_type`, `confidence` | `entities` |
| `complexity_scoring` | `score`, `level` | `factors` |
| `routing` | `route`, `agent_type` | `fallback_used` |
| `context_building` | `session_id`, `token_count` | `messages_count` |
| `memory_recall` | `session_id`, `query`, `results_count` | `retriever_type` |
| `context_compile` | `token_count_in`, `token_count_out` | `truncated_messages` |
| `agent_execution` | `agent_type`, `task_id` | `max_iterations` |
| `model_invocation` | `model`, `provider`, `input_tokens` | `output_tokens`, `finish_reason` |
| `tools_execution` | `tools_count` | `parallelism` |
| `tool_name` | `tool_name`, `status` | `duration_ms`, `error` |
| `response_formation` | `session_id`, `response_length` | `streaming` |
| `session_save` | `session_id`, `operation` | `duration_ms`, `message_count` |

### 10.4 日志级别使用规范

| 级别 | 使用场景 | 示例 |
| ---- | -------- | ---- |
| DEBUG | 详细调试信息，仅开发环境输出 | 路由决策详情、检索查询参数 |
| INFO | 正常业务流程节点 | 任务开始/完成、会话创建/删除、工具调用成功 |
| WARN | 潜在问题但不影响功能 | 重试、限流、上下文压缩、路径违规 |
| ERROR | 操作失败但可恢复 | 工具执行失败、模型调用失败、存储错误 |
| CRITICAL | 系统级错误需立即处理 | 沙箱逃逸、安全违规、认证失败 |

### 10.5 指标采集最佳实践

1. **Counter**：用于累计不可逆事件（请求数、任务数、错误数）
2. **Gauge**：用于记录瞬时值（活跃会话数、队列深度）
3. **Histogram**：用于记录分布（延迟、Token 使用量）
4. **标签规范**：使用 `module_subtype` 格式，如 `task_retry`、`session_active`
5. **Cardinality 控制**：避免使用高基数标签（如 user_id、session_id）

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
| ---- | ---- | -------- | ---- |
| 1.0 | 2026-03-29 | 初始版本 | Architect |
| 1.1 | 2026-03-29 | 汇总各模块可观测性内容 | Architect |

_版本: 1.1_
_更新日期: 2026-03-29_
