"""One-shot check of a repo-scoped GITHUB_TOKEN against owned issue artifacts.

The only mutations rename synthetic artifacts in two researcher-owned repos.
Print status codes only. Never print the short-lived token or response bodies.
"""

import http.client
import json
import os


SOURCE_REPO = "makino-yuto/h1-advisory-boundary-20261109"
TARGET_REPO = "makino-yuto/h1-creation-boundary-20261109-seed"
SOURCE_PATH = f"/repos/{SOURCE_REPO}/issues/1/artifacts/1"
TARGET_PATH = f"/repos/{TARGET_REPO}/issues/2/artifacts/1"
OWN_READ_MARKER = "Owned isolation test"
TARGET_READ_MARKER = "H1_PRIVATE_ISSUE_ARTIFACT_BODY_20261110_M4Q8"


def get_artifact(path: str, token: str) -> tuple[int, str]:
    connection = http.client.HTTPSConnection("api.github.com", timeout=20)
    try:
        connection.request(
            "GET",
            path,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "h1-owned-artifact-scope-test",
                "X-GitHub-Api-Version": "2026-03-10",
            },
        )
        response = connection.getresponse()
        raw = response.read(100_000)
        if response.status != 200:
            return response.status, ""
        value = json.loads(raw)
        return response.status, value.get("artifact", {}).get("body", "")
    finally:
        connection.close()


def patch_name(path: str, name: str, token: str) -> int:
    body = json.dumps({"name": name}).encode("utf-8")
    connection = http.client.HTTPSConnection("api.github.com", timeout=20)
    try:
        connection.request(
            "PATCH",
            path,
            body,
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "h1-owned-artifact-scope-test",
                "X-GitHub-Api-Version": "2026-03-10",
            },
        )
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    mode = os.environ.get("H1_PROBE_MODE", "read")
    if mode == "read":
        own_status, own_body = get_artifact(SOURCE_PATH, token)
        print(f"own_artifact_get_http={own_status}")
        print(f"own_marker_present={OWN_READ_MARKER in own_body}")
        if own_status != 200 or OWN_READ_MARKER not in own_body:
            print("target_artifact_get=skipped_no_positive_control")
            return
        target_status, target_body = get_artifact(TARGET_PATH, token)
        print(f"other_private_artifact_get_http={target_status}")
        print(f"other_private_marker_present={TARGET_READ_MARKER in target_body}")
        return
    if mode != "write":
        raise ValueError("H1_PROBE_MODE must be read or write")
    own_status = patch_name(SOURCE_PATH, "H1 own artifact scope positive 20261110", token)
    print(f"own_artifact_patch_http={own_status}")
    if own_status != 200:
        print("target_artifact_patch=skipped_no_positive_control")
        return
    target_status = patch_name(TARGET_PATH, "H1 cross repo scope test 20261110", token)
    print(f"other_private_artifact_patch_http={target_status}")


if __name__ == "__main__":
    main()
