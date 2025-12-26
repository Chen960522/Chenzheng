# Python 版本要求

## 支持的 Python 版本

本项目支持 **Python 3.9+**

## 版本兼容性

- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12

## 依赖包说明

所有依赖包都已验证与 Python 3.9+ 兼容。

### 关键依赖

- **FastAPI**: 现代化的 Web 框架
- **Boto3**: AWS SDK
- **Pydantic**: 数据验证
- **Uvicorn**: ASGI 服务器

### 已移除的依赖

- `pydantic-settings`: 在某些 Python 版本上可能不兼容，已改用 `python-dotenv` 直接加载环境变量

## 类型注解兼容性

代码中的类型注解已更新为 Python 3.9 兼容格式：

- ✅ 使用 `Tuple[...]` 而不是 `tuple[...]`
- ✅ 使用 `List[...]` 而不是 `list[...]`
- ✅ 使用 `Dict[...]` 而不是 `dict[...]`
- ✅ 从 `typing` 模块导入类型

## 验证 Python 版本

```bash
python3 --version
# 应该显示 Python 3.9.x 或更高版本
```

## 安装依赖

```bash
# 确保使用 Python 3.9+
python3 -m pip install -r requirements.txt
```
