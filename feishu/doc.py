"""Markdown 报告导入为飞书云文档（docx），返回文档 URL。"""
import time


def import_markdown(client, md_path, doc_title):
    """上传 md → 创建导入任务 → 轮询结果。返回 (doc_token, doc_url)。"""
    file_token = client.upload_for_import(md_path, doc_title + ".md")

    r = client.request("POST", "/drive/v1/import_tasks", data={
        "file_extension": "md",
        "file_token": file_token,
        "type": "docx",
        "file_name": doc_title,
        "point": {"mount_type": 1, "mount_key": ""},
    })
    if r.get("code") != 0:
        raise RuntimeError(f"import task create failed: {r}")
    ticket = r["data"]["ticket"]

    for _ in range(20):
        time.sleep(2)
        r = client.request("GET", f"/drive/v1/import_tasks/{ticket}")
        if r.get("code") != 0:
            continue
        result = r["data"]["result"]
        job_status = result.get("job_status")
        if job_status == 0:
            return result["token"], result["url"]
        if job_status not in (1, 2):
            raise RuntimeError(f"import job failed: {result}")
    raise RuntimeError("import job timeout")


def make_tenant_readable(client, doc_token):
    """尝试将文档设为组织内可读，失败不阻塞。"""
    r = client.request(
        "PATCH", f"/drive/v1/permissions/{doc_token}/public?type=docx",
        data={"link_share_entity": "tenant_readable"},
    )
    return r.get("code") == 0
