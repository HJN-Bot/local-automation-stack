# Airtable Schema Patch — TaskStateLog

## 需要新增的三个字段

在 Airtable 的 TaskStateLog 表（`tblmb8402TJiPz5h9`）中手动添加以下字段：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `LockToken` | Single line text | UUID，标记当前持有锁的 token；空 = 未锁 |
| `LeaseUntil` | Date（含时间，ISO 8601） | 锁的过期时间；harness 只信任此字段，不信任外部时钟 |
| `LeaseOwner` | Single line text | 持锁进程的标识（hostname-harness），便于调试 |

## 添加步骤

1. 打开 Airtable → TaskStateLog 表
2. 点击最右侧 **+** 添加字段
3. 依次添加上表三个字段，类型如上
4. 保存

## 验证

添加后在任意一条记录上手动填入测试值，然后运行：
```bash
python3 - <<'EOF'
from pyairtable import Api
import os; from dotenv import load_dotenv; load_dotenv()
tbl = Api(os.environ["AIRTABLE_API_KEY"]).base(os.environ["AIRTABLE_BASE_ID"]).table("tblmb8402TJiPz5h9")
rec = tbl.first()
print(rec["fields"].get("LockToken"), rec["fields"].get("LeaseUntil"), rec["fields"].get("LeaseOwner"))
EOF
```
如果输出不报 KeyError，说明字段已正确创建。

## 注意

- `LockToken` 和 `LeaseUntil` 留空 = 未锁定，harness 可认领
- 不要给这三个字段设默认值
- `LeaseUntil` 的 Airtable 格式选 **Date** → 开启 **Include time** → 格式选 **ISO 8601**
