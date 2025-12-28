# 异步PR处理说明

## 问题背景

当同时提交多个PR时,原版本的Flask应用会出现阻塞问题:
- Flask开发服务器默认是单线程的
- PR分析需要几分钟时间
- 其他PR的webhook请求会被阻塞
- GitHub webhook期望10秒内收到响应

## 解决方案

### 架构改进

采用**生产者-消费者模式**的异步任务队列:

```
GitHub Webhook → Flask Server → 任务队列 → 工作线程池 → PR处理
                      ↓
                  立即返回202
```

### 核心组件

#### 1. **任务队列 (Queue)**
- 线程安全的FIFO队列
- 缓存所有待处理的PR任务

#### 2. **工作线程池**
- 默认3个后台工作线程
- 可并行处理多个PR
- 每个线程独立处理一个PR

#### 3. **异步响应**
- Webhook收到请求后立即返回 `202 Accepted`
- 不等待PR处理完成
- 避免GitHub webhook超时

## 工作流程

### 1. 接收Webhook (秒级)
```python
POST /webhook
↓
验证签名
↓
创建PRTask
↓
放入队列
↓
立即返回 202 Accepted
```

### 2. 后台处理 (分钟级)
```python
Worker线程从队列获取任务
↓
克隆代码仓库
↓
运行LangGraph工作流
↓
生成审查报告
↓
发布到GitHub
↓
清理资源
↓
标记任务完成
```

## 关键特性

### ✅ 并行处理
- 最多3个PR可以同时处理
- 其他PR在队列中等待
- 不会丢失任何webhook请求

### ✅ 快速响应
- Webhook请求<1秒返回
- GitHub立即收到确认
- 避免webhook重试

### ✅ 线程安全
- 使用Queue保证线程安全
- 每个任务独立处理
- 错误不会影响其他任务

### ✅ 可观测性
- 日志包含线程名称
- 实时队列状态查询
- `/queue` 端点监控

## 配置说明

### 调整并行数

修改 `app.py` 中的 `MAX_WORKERS`:

```python
MAX_WORKERS = 3  # 根据服务器资源调整
```

建议:
- 小型服务器: 1-2个worker
- 中型服务器: 3-5个worker
- 大型服务器: 5-10个worker

### 资源考虑

每个worker需要:
- CPU: 1-2核心
- 内存: 2-4GB
- 磁盘: 临时仓库空间

## API端点

### Webhook端点
```
POST /webhook
```
响应: `202 Accepted` (立即返回)

### 健康检查
```
GET /health
```
响应:
```json
{
  "status": "healthy",
  "queue_size": 2,
  "active_workers": 3
}
```

### 队列状态
```
GET /queue
```
响应:
```json
{
  "queue_size": 2,
  "active_workers": 3,
  "max_workers": 3
}
```

## 日志示例

```
[INFO] Received event: pull_request
[INFO] PR #123 action: opened in user/repo
[INFO] ✓ PR #123 added to queue (queue size: 1)
[INFO] [Worker-1] Worker picked up PRTask(PR#123 in user/repo)
[INFO] [Worker-1] Starting PR #123 processing in user/repo
[INFO] [Worker-1] Exporting PR #123
...
[INFO] [Worker-1] ✓ PR #123 processing completed successfully
```

## 注意事项

### 1. 任务不保证顺序
- 先提交的PR可能后完成
- 取决于PR复杂度和资源可用性

### 2. 服务器重启
- 重启会清空队列
- 未完成的任务会丢失
- 建议: 使用持久化队列(Redis/Celery)

### 3. 资源限制
- 同时处理的PR受worker数量限制
- 过多PR可能导致资源耗尽
- 监控队列大小,必要时扩容

## 性能优化建议

### 1. 使用生产级WSGI服务器
```bash
gunicorn -w 4 -k gevent app:app
```

### 2. 使用Redis + Celery
- 任务持久化
- 分布式处理
- 更好的可扩展性

### 3. 添加速率限制
- 防止队列爆炸
- 限制最大队列长度

### 4. 监控告警
- 队列积压告警
- Worker失败告警
- 处理时间监控

## 故障排查

### 队列积压
```bash
# 查看队列状态
curl http://localhost:3000/queue

# 增加worker数量
# 修改 MAX_WORKERS 并重启
```

### Worker卡死
```bash
# 查看日志
sudo docker logs wise-code-watchers

# 重启服务
sudo docker restart wise-code-watchers
```

### 内存不足
```bash
# 监控内存
docker stats

# 减少worker数量
# 优化workflow参数(top_n, batch_size)
```
