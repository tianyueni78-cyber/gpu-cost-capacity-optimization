class SupabaseForecastStore:
    """Thin append-only adapter; pass a Supabase client in hosted mode."""

    def __init__(self, user_id, client=None):
        if not user_id:
            raise ValueError("请先登录")
        self.user_id = user_id
        self.client = client
        self._local_versions = {}

    def append_forecast_version(self, values):
        version_id = values["version_id"]
        payload = {**values, "owner_id": self.user_id}
        if self.client is None:
            if version_id in self._local_versions:
                raise ValueError("预测版本已存在")
            self._local_versions[version_id] = payload
            return payload.copy()
        try:
            result = self.client.table("forecast_versions").insert(payload).execute()
            return result.data[0]
        except Exception as exc:
            raise RuntimeError("预测版本保存失败，请检查项目权限或版本编号") from exc
