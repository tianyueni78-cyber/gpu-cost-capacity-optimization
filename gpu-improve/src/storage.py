class StorageError(RuntimeError):
    pass


class SupabaseStore:
    """使用登录用户 JWT 的薄存储层；数据隔离由数据库 RLS 强制执行。"""

    def __init__(self, client, user_id: str):
        if not user_id:
            raise StorageError("请先登录")
        self.client = client
        self.user_id = user_id

    def _insert(self, table: str, payload: dict, allow_owner: bool = False):
        try:
            clean = payload if allow_owner else {
                key: value for key, value in payload.items() if key != "owner_id"
            }
            return self.client.table(table).insert(clean).execute().data
        except Exception as exc:
            raise StorageError("数据库操作失败，请检查连接和权限") from None

    def create_project(self, name: str):
        return self._insert(
            "projects", {"name": name, "owner_id": self.user_id}, allow_owner=True
        )

    def save_action(self, project_id: str, payload: dict):
        return self._insert("actions", {**payload, "project_id": project_id})

    def append_event(self, project_id: str, payload: dict):
        return self._insert("action_events", {**payload, "project_id": project_id})

    def save_baseline(self, project_id: str, payload: dict):
        return self._insert("baselines", {**payload, "project_id": project_id})

    def save_measurement(self, project_id: str, payload: dict):
        return self._insert("measurements", {**payload, "project_id": project_id})

    def save_benefit_result(self, project_id: str, payload: dict):
        return self._insert("benefit_results", {**payload, "project_id": project_id})

    def list_rows(self, table: str, project_id: str):
        allowed = {
            "actions", "action_events", "baselines", "measurements", "benefit_results"
        }
        if table not in allowed:
            raise StorageError("不支持的数据对象")
        try:
            return self.client.table(table).select("*").eq("project_id", project_id).execute().data
        except Exception:
            raise StorageError("数据库操作失败，请检查连接和权限") from None
