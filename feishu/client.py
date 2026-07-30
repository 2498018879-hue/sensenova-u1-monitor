"""飞书 API 客户端：鉴权、JSON 请求、文件上传（标准库实现）。"""
import json
import os
import urllib.request
import uuid

BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    def __init__(self, app_id=None, app_secret=None):
        self.app_id = app_id or os.environ["FEISHU_APP_ID"]
        self.app_secret = app_secret or os.environ["FEISHU_APP_SECRET"]
        self._token = None

    def token(self):
        if self._token:
            return self._token
        r = self.request(
            "POST", "/auth/v3/tenant_access_token/internal",
            data={"app_id": self.app_id, "app_secret": self.app_secret}, auth=False,
        )
        if r.get("code") != 0:
            raise RuntimeError(f"feishu auth failed: {r}")
        self._token = r["tenant_access_token"]
        return self._token

    def request(self, method, path, data=None, auth=True):
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if auth:
            headers["Authorization"] = f"Bearer {self.token()}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode())

    def upload_for_import(self, file_path, file_name):
        """上传素材用于导入云文档（parent_type=ccm_import_open）。返回 file_token。"""
        boundary = uuid.uuid4().hex
        size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        extra = json.dumps({"obj_type": "docx", "file_extension": "md"})
        fields = {
            "file_name": file_name,
            "parent_type": "ccm_import_open",
            "size": str(size),
            "extra": extra,
        }
        parts = b""
        for k, v in fields.items():
            parts += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
            ).encode()
        parts += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{file_name}\"\r\nContent-Type: text/markdown\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            BASE + "/drive/v1/medias/upload_all",
            data=parts,
            headers={
                "Authorization": f"Bearer {self.token()}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                r = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            r = json.loads(e.read().decode())
        if r.get("code") != 0:
            raise RuntimeError(f"upload failed: {r}")
        return r["data"]["file_token"]
