#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: MIT
"""Call AIDAP bootstrap APIs not exposed by the current ve CLI."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import quote, urlencode


DEFAULT_REGION = "cn-beijing"
DEFAULT_HOST = "open.volcengineapi.com"


API_REGISTRY = {
    "get-verify-info": {
        "service": "account_verify",
        "action": "GetVerifyInfo",
        "version": "2018-01-01",
        "method": "POST",
        "body": {},
        "summary": "Check whether the account has enterprise real-name verification.",
    },
}


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def norm_query(params: dict[str, Any]) -> str:
    pairs: list[str] = []
    for key in sorted(params.keys()):
        value = params[key]
        if isinstance(value, list):
            for item in value:
                pairs.append(f"{quote(key, safe='-_.~')}={quote(str(item), safe='-_.~')}")
        else:
            pairs.append(f"{quote(key, safe='-_.~')}={quote(str(value), safe='-_.~')}")
    return "&".join(pairs).replace("+", "%20")


def hmac_sha256(key: bytes, content: str) -> bytes:
    return hmac.new(key, content.encode("utf-8"), hashlib.sha256).digest()


def hash_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON for --params: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("--params must be a JSON object")
    return payload


def summarize_verify_info(payload: Any) -> dict[str, Any]:
    info = payload.get("Result", payload) if isinstance(payload, dict) else {}
    if not isinstance(info, dict):
        info = {}
    is_verified = info.get("IsVerified") is True
    identity_type = info.get("IdentityType")
    return {
        "is_verified": is_verified,
        "identity_type": identity_type,
        "enterprise_verified": is_verified and identity_type == "enterprise",
    }


def signed_action_request(
    *,
    ak: str,
    sk: str,
    session_token: str,
    region: str,
    host: str,
    service: str,
    version: str,
    action: str,
    method: str,
    body: dict[str, Any],
    scheme: str,
    content_type: str = "application/json",
) -> tuple[Any, int]:
    method = method.upper()
    if method == "GET":
        request_query = {"Action": action, "Version": version, **body}
        body_str = ""
    else:
        request_query = {"Action": action, "Version": version}
        body_str = urlencode(body, doseq=True) if content_type == "application/x-www-form-urlencoded" else json.dumps(body)

    x_date = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_date = x_date[:8]
    body_hash = hash_sha256(body_str)
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join(
        [
            method,
            "/",
            norm_query(request_query),
            "\n".join(
                [
                    f"content-type:{content_type}",
                    f"host:{host}",
                    f"x-content-sha256:{body_hash}",
                    f"x-date:{x_date}",
                ]
            ),
            "",
            signed_headers,
            body_hash,
        ]
    )
    credential_scope = "/".join([short_date, region, service, "request"])
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, credential_scope, hash_sha256(canonical_request)])
    k_date = hmac_sha256(sk.encode("utf-8"), short_date)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    k_signing = hmac_sha256(k_service, "request")
    signature = hmac_sha256(k_signing, string_to_sign).hex()
    headers = {
        "Host": host,
        "X-Content-Sha256": body_hash,
        "X-Date": x_date,
        "Content-Type": content_type,
        "Authorization": (
            f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
    }
    if session_token:
        headers["X-Security-Token"] = session_token

    url = f"{scheme}://{host}/?{norm_query(request_query)}"
    data = None if method == "GET" else body_str.encode("utf-8")
    req = urllib_request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            status_code = response.status
            response_text = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        status_code = exc.code
        response_text = exc.read().decode("utf-8")

    try:
        payload: Any = json.loads(response_text)
    except json.JSONDecodeError:
        payload = response_text
    return payload, status_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=sorted(API_REGISTRY))
    parser.add_argument("--params", help="JSON object merged into the default request body")
    parser.add_argument("--region", default=env("VOLCENGINE_REGION", DEFAULT_REGION))
    parser.add_argument("--host", default=env("VOLCENGINE_ENDPOINT", DEFAULT_HOST))
    parser.add_argument("--scheme", default="https", choices=["http", "https"])
    parser.add_argument("--method", choices=["GET", "POST"])
    parser.add_argument("--content-type", default="application/json")
    parser.add_argument("--output", choices=["json", "pretty"], default="json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ak = env("VOLCENGINE_ACCESS_KEY")
    sk = env("VOLCENGINE_SECRET_KEY")
    if not ak or not sk:
        print("VOLCENGINE_ACCESS_KEY and VOLCENGINE_SECRET_KEY are required", file=sys.stderr)
        return 2

    spec = API_REGISTRY[args.operation]
    body = dict(spec["body"])
    body.update(parse_json(args.params))
    payload, status_code = signed_action_request(
        ak=ak,
        sk=sk,
        session_token=env("VOLCENGINE_SESSION_TOKEN", "") or "",
        region=args.region,
        host=args.host,
        service=spec["service"],
        version=spec["version"],
        action=spec["action"],
        method=args.method or spec["method"],
        body=body,
        scheme=args.scheme,
        content_type=args.content_type,
    )
    result = {
        "operation": args.operation,
        "service": spec["service"],
        "action": spec["action"],
        "version": spec["version"],
        "status_code": status_code,
        "response": payload,
    }
    if args.operation == "get-verify-info":
        result["verification"] = summarize_verify_info(payload)
    if args.output == "pretty":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if 200 <= status_code < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
