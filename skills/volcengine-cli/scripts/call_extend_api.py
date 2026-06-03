#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: MIT
"""
Call selected Volcengine extension APIs.

This helper intentionally keeps the Universal client code inline and does not import
from any external repository.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import json
import os
import sys
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import quote, urlencode

try:
    from volcenginesdkcore import UniversalApi, UniversalInfo, ApiClient, Configuration
except ImportError as exc:  # pragma: no cover - depends on user environment
    print(
        "Missing dependency: volcenginesdkcore. Install the Volcengine Python SDK before using this script.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


DEFAULT_REGION = "cn-beijing"
DEFAULT_HOST = "open.volcengineapi.com"


def create_universal_info(service, action, version="2021-09-01", method="POST", content_type="application/json"):
    if content_type is None:
        content_type = "application/json"
    if method == "GET":
        content_type = "text/plain"

    return UniversalInfo(
        method=method,
        service=service,
        version=version,
        action=action,
        content_type=content_type,
    )


def create_api_client(ak, sk, session_token="", region=DEFAULT_REGION, host=DEFAULT_HOST, scheme="https"):
    config = Configuration()
    config.ak = ak
    config.sk = sk
    config.host = host
    config.scheme = scheme
    config.region = region
    if session_token:
        config.session_token = session_token

    return UniversalApi(ApiClient(config))


API_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "DescribeOriginTopStatisticalData",
        "service": "CDN",
        "version": "2021-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "cdn.volcengineapi.com",
        "scheme": "https",
        "call_style": "action_version",
        "summary": "CDN origin-side top statistical data.",
    },
    {
        "name": "ListPipelineRunStagesInner",
        "service": "cp",
        "version": "2023-05-01",
        "method": "POST",
        "content_type": "application/json",
        "call_style": "universal",
        "summary": "CodePipeline internal stage list for a pipeline run, used to inspect failed stages/tasks.",
    },
    {
        "name": "DescribeRealtimeData",
        "service": "dcdn",
        "version": "2021-04-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "DCDN realtime edge data.",
    },
    {
        "name": "DescribeOriginRealtimeData",
        "service": "dcdn",
        "version": "2021-04-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "DCDN realtime origin data.",
    },
    {
        "name": "DescribeTopIPs",
        "service": "dcdn",
        "version": "2021-04-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "DCDN top client IP ranking.",
    },
    {
        "name": "DescribeTopReferers",
        "service": "dcdn",
        "version": "2021-04-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "DCDN top referer ranking.",
    },
    {
        "name": "DescribeTopUrls",
        "service": "dcdn",
        "version": "2021-04-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "DCDN top URL ranking.",
    },
    {
        "name": "DescribeListenerLogs",
        "service": "ga",
        "version": "2022-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "Global Accelerator listener logs.",
    },
    {
        "name": "GetAcceleratorDimension",
        "service": "ga",
        "version": "2022-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "Global Accelerator metric dimensions for accelerator resources.",
    },
    {
        "name": "GetBandwidthPackage",
        "service": "ga",
        "version": "2022-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "Global Accelerator bandwidth package detail.",
    },
    {
        "name": "GetBasicEndpointRelatedAccInstanceInfos",
        "service": "ga",
        "version": "2022-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "Global Accelerator related basic accelerator instance info for an endpoint.",
    },
    {
        "name": "GetEndpointRelatedAccInstanceInfos",
        "service": "ga",
        "version": "2022-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "Global Accelerator related accelerator instance info for an endpoint.",
    },
    {
        "name": "ListAccelerateAreas",
        "service": "ga",
        "version": "2022-03-01",
        "method": "GET",
        "content_type": "text/plain",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "List Global Accelerator acceleration areas.",
    },
    {
        "name": "ListBandwidthPackages",
        "service": "ga",
        "version": "2022-03-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "List Global Accelerator bandwidth packages.",
    },
    {
        "name": "DescribeLiveBatchStreamTranscodeData",
        "service": "live",
        "version": "2023-01-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "live.volcengineapi.com",
        "scheme": "https",
        "call_style": "action_version",
        "summary": "Live batch stream transcode data.",
    },
    {
        "name": "DescribeLiveBatchStreamSessionData",
        "service": "live",
        "version": "2023-01-01",
        "method": "POST",
        "content_type": "application/json",
        "host": "live.volcengineapi.com",
        "scheme": "https",
        "call_style": "action_version",
        "summary": "Live batch stream session data.",
    },
    {
        "name": "DescribeCdnDomainConfig",
        "service": "mcdn",
        "version": "2022-03-01",
        "method": "GET",
        "content_type": "text/plain",
        "host": "open.volcengineapi.com",
        "scheme": "http",
        "call_style": "action_version",
        "summary": "MCDN CDN domain configuration.",
    },
    {
        "name": "CreateVirtualNode",
        "service": "vke",
        "version": "2022-05-12",
        "method": "POST",
        "content_type": "application/json",
        "call_style": "universal",
        "summary": "Create a VKE virtual node.",
    },
    {
        "name": "ListVirtualNodes",
        "service": "vke",
        "version": "2022-05-12",
        "method": "POST",
        "content_type": "application/json",
        "call_style": "universal",
        "summary": "List VKE virtual nodes.",
    },
    {
        "name": "QueryMetrics",
        "service": "vmp",
        "version": "2021-03-03",
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "query_keys": ["workspace"],
        "host_template": "vmp.{region}.volcengineapi.com",
        "scheme": "https",
        "summary": "VMP instant PromQL query for a workspace.",
    },
    {
        "name": "QueryMetricsRange",
        "service": "vmp",
        "version": "2021-03-03",
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "query_keys": ["workspace"],
        "host_template": "vmp.{region}.volcengineapi.com",
        "scheme": "https",
        "summary": "VMP range PromQL query for a workspace.",
    },
    {
        "name": "GetLabelValues",
        "service": "vmp",
        "version": "2021-03-03",
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "query_keys": ["workspace", "label"],
        "host_template": "vmp.{region}.volcengineapi.com",
        "scheme": "https",
        "summary": "VMP label values query.",
    },
    {
        "name": "GetLabels",
        "service": "vmp",
        "version": "2021-03-03",
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "query_keys": ["workspace"],
        "host_template": "vmp.{region}.volcengineapi.com",
        "scheme": "https",
        "summary": "VMP label names query.",
    },
    {
        "name": "GetSeries",
        "service": "vmp",
        "version": "2021-03-03",
        "method": "POST",
        "content_type": "application/x-www-form-urlencoded",
        "query_keys": ["workspace"],
        "host_template": "vmp.{region}.volcengineapi.com",
        "scheme": "https",
        "summary": "VMP series query.",
    },
]


def add_actions(
    names: list[str],
    *,
    service: str,
    version: str,
    method: str,
    summary_prefix: str,
    content_type: str = "application/json",
    host: str | None = None,
    host_template: str | None = None,
    scheme: str | None = None,
    call_style: str = "action_version",
    query_keys: list[str] | None = None,
    preserve_query_keys_in_body: list[str] | None = None,
    test_only: bool = False,
) -> None:
    for name in names:
        entry = {
            "name": name,
            "service": service,
            "version": version,
            "method": method,
            "content_type": content_type,
            "call_style": call_style,
            "summary": f"{summary_prefix}: {name}.",
        }
        if host:
            entry["host"] = host
        if host_template:
            entry["host_template"] = host_template
        if scheme:
            entry["scheme"] = scheme
        if query_keys:
            entry["query_keys"] = query_keys
        if preserve_query_keys_in_body:
            entry["preserve_query_keys_in_body"] = preserve_query_keys_in_body
        if test_only:
            entry["test_only"] = True
        API_REGISTRY.append(entry)


add_actions(
    [
        "RunAlertInvestigator",
        "RunPcapAnalyzer",
        "RunAlertFormatter",
        "RunThreatIntelProducer",
        "RunWebRiskAssessor",
        "RunDlpScreenshotAnalyzer",
        "RunSensitiveDataDetector",
    ],
    service="sec_agent",
    version="2025-01-01",
    method="POST",
    summary_prefix="Security intelligent workflow",
    host="open.volcengineapi.com",
    scheme="https",
)

add_actions(
    ["CheckFee", "GetDomain", "GetAsyncTask", "GetTemplate", "ListDomains", "ListTemplates"],
    service="domain_openapi",
    version="2022-12-12",
    method="GET",
    summary_prefix="Domain service",
    content_type="text/plain",
    host="open.volcengineapi.com",
    scheme="http",
)
add_actions(
    ["RegisterDomain"],
    service="domain_openapi",
    version="2022-12-12",
    method="POST",
    summary_prefix="Domain service",
    host="open.volcengineapi.com",
    scheme="http",
)

add_actions(
    [
        "CallService",
        "GetAllLastDevicePropertyValue",
        "GetCustomTopicList",
        "GetDeviceDetail",
        "GetDeviceEventRecordList",
        "GetDeviceList",
        "GetDeviceOverview",
        "GetDeviceStatus",
        "GetDeviceServiceCallRecordList",
        "GetInstanceDetail",
        "GetInstanceEndpoints",
        "GetInstanceList",
        "GetLastDevicePropertyValue",
        "GetProductList",
        "GetProductDetail",
        "GetPropertyValuesByTime",
        "GetThingModel",
        "SetProperty",
    ],
    service="iot",
    version="2021-12-14",
    method="POST",
    summary_prefix="IoT device or instance operation",
    host="iot.cn-shanghai.volcengineapi.com",
    scheme="https",
)

add_actions(
    ["GetApplicant", "GetTrademark", "ListApplicants", "GetRequirement", "ListRequirements", "ListTrademarks", "ListBarrierTrademarks"],
    service="trademark",
    version="2023-06-01",
    method="GET",
    summary_prefix="Trademark query",
    content_type="text/plain",
    host="open.volcengineapi.com",
    scheme="http",
)
add_actions(
    ["SearchTrademarkInfo", "SearchTrademark"],
    service="trademark",
    version="2023-06-01",
    method="POST",
    summary_prefix="Trademark search",
    host="open.volcengineapi.com",
    scheme="http",
)

add_actions(
    ["ListWorkspace", "GetWorkspaceInfo", "ListQueryClusters", "GetQueryCluster", "ListPreagg", "InfluxQuery", "MetricsQuery"],
    service="metrics",
    version="2024-06-29",
    method="POST",
    summary_prefix="Volcengine Metrics service",
    host_template="metrics.{region}.volcengineapi.com",
    scheme="https",
)

add_actions(
    [
        "StartCloudServer",
        "StopCloudServer",
        "RebootCloudServer",
    ],
    service="veenedge",
    version="2021-04-30",
    method="POST",
    summary_prefix="VEEN edge cloud mutation",
    host="veenedge.volcengineapi.com",
)
add_actions(
    [
        "GetVEENInstanceUsage",
        "GetVEEWInstanceUsage",
        "GetBandwidthUsage",
        "GetBillingUsageDetail",
    ],
    service="veenedge",
    version="2021-04-30",
    method="GET",
    summary_prefix="VEEN edge cloud query",
    content_type="text/plain",
    host="veenedge.volcengineapi.com",
)

add_actions(
    ["ListGMSProject", "GetGMSProjectDetail", "GetGRSAppById"],
    service="flink",
    version="2021-06-01",
    method="GET",
    summary_prefix="Flink management query",
    content_type="text/plain",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
)
add_actions(
    ["ListGMCSResourcePool"],
    service="flink",
    version="2022-06-01",
    method="GET",
    summary_prefix="Flink management query",
    content_type="text/plain",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
)
add_actions(
    ["ListGASLogs", "GetGWSApplication"],
    service="flink",
    version="2021-06-01",
    method="POST",
    summary_prefix="Flink GWS/GAS operation",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
)
add_actions(
    ["ListGWSDirectory"],
    service="flink",
    version="2021-06-01",
    method="POST",
    summary_prefix="Flink GWS/GAS operation",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
    query_keys=["ProjectId", "Type"],
)
add_actions(
    ["GetGWSApplicationDraft", "DeleteGWSApplication", "GWSGetEventList", "StartGWSApplication", "CancelGWSApplication", "RestartGWSApplication"],
    service="flink",
    version="2021-06-01",
    method="POST",
    summary_prefix="Flink GWS/GAS operation",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
    query_keys=["ProjectId"],
)
add_actions(
    ["CreateGWSApplicationDraft", "UpdateGWSApplicationDraft"],
    service="flink",
    version="2021-06-01",
    method="POST",
    summary_prefix="Flink GWS/GAS operation",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
    query_keys=["ProjectId"],
    preserve_query_keys_in_body=["ProjectId"],
)
add_actions(
    ["DeployGWSApplicationDraft"],
    service="flink",
    version="2021-06-01",
    method="POST",
    summary_prefix="Flink GWS/GAS operation",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
    query_keys=["ProjectId", "Id"],
)
add_actions(
    ["ListGWSApplication"],
    service="flink",
    version="2021-06-01",
    method="POST",
    summary_prefix="Flink GWS/GAS operation",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
    query_keys=["PageSize", "PageNum", "SortField", "SortOrder"],
)
add_actions(
    ["GetGMSUserToken"],
    service="flink",
    version="2021-06-01",
    method="GET",
    summary_prefix="Flink test-only token query",
    content_type="text/plain",
    host="open.volcengineapi.com",
    scheme="https",
    call_style="flink_path",
    test_only=True,
)


_REGION_BY_SERVICE = {
    "CDN": "cn-north-1",
    "dcdn": "cn-north-1",
    "ga": "cn-north-1",
    "live": "cn-north-1",
    "mcdn": "cn-north-1",
    "domain_openapi": "cn-north-1",
    "trademark": "cn-north-1",
    "veenedge": "cn-north-1",
    "iot": "cn-shanghai",
}
for _entry in API_REGISTRY:
    _region = _REGION_BY_SERVICE.get(_entry["service"])
    if _region:
        _entry["region"] = _region


def parse_json_value(raw: str | None) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if raw.startswith("@"):
        with open(raw[1:], "r", encoding="utf-8") as f:
            raw = f.read()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for --params: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("--params must be a JSON object")
    return value


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def split_query_body(
    params: dict[str, Any],
    query_keys: list[str] | None,
    preserve_query_keys_in_body: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not query_keys:
        return {}, params
    preserve_query_keys_in_body = preserve_query_keys_in_body or []
    query: dict[str, Any] = {}
    body: dict[str, Any] = {}
    for key, value in params.items():
        if key in query_keys:
            query[key] = value
        if key not in query_keys or key in preserve_query_keys_in_body:
            body[key] = value
    return query, body


def norm_query(params: dict[str, Any]) -> str:
    query = ""
    for key in sorted(params.keys()):
        value = params[key]
        if isinstance(value, list):
            for item in value:
                query += quote(key, safe="-_.~") + "=" + quote(str(item), safe="-_.~") + "&"
        else:
            query += quote(key, safe="-_.~") + "=" + quote(str(value), safe="-_.~") + "&"
    return query[:-1].replace("+", "%20")


def hmac_sha256(key: bytes, content: str) -> bytes:
    return hmac.new(key, content.encode("utf-8"), hashlib.sha256).digest()


def hash_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def signed_post_with_query(
    *,
    ak: str,
    sk: str,
    session_token: str,
    region: str,
    host: str,
    service: str,
    version: str,
    action: str,
    content_type: str,
    query: dict[str, Any],
    body: dict[str, Any],
    scheme: str,
) -> tuple[Any, int, dict[str, str]]:
    if content_type == "application/x-www-form-urlencoded":
        body_str = urlencode(body, doseq=True)
    else:
        body_str = json.dumps(body)

    request_query = {"Action": action, "Version": version, **query}
    x_date = utc_now().strftime("%Y%m%dT%H%M%SZ")
    short_x_date = x_date[:8]
    x_content_sha256 = hash_sha256(body_str)
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            norm_query(request_query),
            "\n".join(
                [
                    "content-type:" + content_type,
                    "host:" + host,
                    "x-content-sha256:" + x_content_sha256,
                    "x-date:" + x_date,
                ]
            ),
            "",
            signed_headers,
            x_content_sha256,
        ]
    )
    credential_scope = "/".join([short_x_date, region, service, "request"])
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, credential_scope, hash_sha256(canonical_request)])
    k_date = hmac_sha256(sk.encode("utf-8"), short_x_date)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    k_signing = hmac_sha256(k_service, "request")
    signature = hmac_sha256(k_signing, string_to_sign).hex()
    headers = {
        "Host": host,
        "X-Content-Sha256": x_content_sha256,
        "X-Date": x_date,
        "Content-Type": content_type,
        "Authorization": (
            "HMAC-SHA256 Credential="
            + ak
            + "/"
            + credential_scope
            + ", SignedHeaders="
            + signed_headers
            + ", Signature="
            + signature
        ),
    }
    if session_token:
        headers["x-security-token"] = session_token

    url = f"{scheme}://{host}/?{norm_query(request_query)}"
    req = urllib_request.Request(
        url=url,
        data=body_str.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            status_code = response.status
            response_headers = dict(response.headers.items())
            response_text = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        status_code = exc.code
        response_headers = dict(exc.headers.items())
        response_text = exc.read().decode("utf-8")

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        payload = response_text
    return payload, status_code, response_headers


def signed_action_version_request(
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
    content_type: str,
    query: dict[str, Any],
    body: dict[str, Any],
    scheme: str,
) -> tuple[Any, int, dict[str, str]]:
    method = method.upper()
    if method == "GET":
        request_query = {"Action": action, "Version": version, **body, **query}
        body_str = ""
    else:
        request_query = {"Action": action, "Version": version, **query}
        if content_type == "application/x-www-form-urlencoded":
            body_str = urlencode(body, doseq=True)
        else:
            body_str = json.dumps(body)

    x_date = utc_now().strftime("%Y%m%dT%H%M%SZ")
    short_x_date = x_date[:8]
    x_content_sha256 = hash_sha256(body_str)
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join(
        [
            method,
            "/",
            norm_query(request_query),
            "\n".join(
                [
                    "content-type:" + content_type,
                    "host:" + host,
                    "x-content-sha256:" + x_content_sha256,
                    "x-date:" + x_date,
                ]
            ),
            "",
            signed_headers,
            x_content_sha256,
        ]
    )
    credential_scope = "/".join([short_x_date, region, service, "request"])
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, credential_scope, hash_sha256(canonical_request)])
    k_date = hmac_sha256(sk.encode("utf-8"), short_x_date)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    k_signing = hmac_sha256(k_service, "request")
    signature = hmac_sha256(k_signing, string_to_sign).hex()
    headers = {
        "Host": host,
        "X-Content-Sha256": x_content_sha256,
        "X-Date": x_date,
        "Content-Type": content_type,
        "Authorization": (
            "HMAC-SHA256 Credential="
            + ak
            + "/"
            + credential_scope
            + ", SignedHeaders="
            + signed_headers
            + ", Signature="
            + signature
        ),
    }
    if session_token:
        headers["x-security-token"] = session_token

    url = f"{scheme}://{host}/?{norm_query(request_query)}"
    data = None if method == "GET" else body_str.encode("utf-8")
    req = urllib_request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            status_code = response.status
            response_headers = dict(response.headers.items())
            response_text = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        status_code = exc.code
        response_headers = dict(exc.headers.items())
        response_text = exc.read().decode("utf-8")

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        payload = response_text
    return payload, status_code, response_headers


def call_flink_path(
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
    content_type: str,
    params: dict[str, Any],
    query_keys: list[str] | None,
    preserve_query_keys_in_body: list[str] | None,
    scheme: str,
) -> tuple[Any, int, dict[str, str]]:
    configuration = Configuration()
    configuration.host = host
    configuration.scheme = scheme
    configuration.ak = ak
    configuration.sk = sk
    configuration.region = region
    if session_token:
        configuration.session_token = session_token
    client = ApiClient(configuration)
    headers = {
        "Accept": client.select_header_accept(["application/json"]),
        "Content-Type": client.select_header_content_type([content_type]),
    }
    if method == "GET":
        query_params = list(params.items())
        body_params = {}
    else:
        query, body = split_query_body(params, query_keys, preserve_query_keys_in_body)
        query_params = list(query.items())
        body_params = body
    path = f"/{action}/{version}/{service}/{method.lower()}/{content_type.lower().replace('/', '_')}"
    response = client.call_api(
        path,
        method,
        {},
        query_params,
        headers,
        body=body_params,
        post_params=[],
        files={},
        response_type=object,
        auth_settings=["volcengineSign"],
        async_req=False,
        _return_http_data_only=False,
        _preload_content=True,
        _request_timeout=None,
        collection_formats={},
    )
    if isinstance(response, tuple) and len(response) == 3:
        return response
    return response, 200, {}


def resolve_host(entry: dict[str, Any], region: str, explicit_host: str | None) -> str:
    if explicit_host:
        return explicit_host
    if entry.get("host_template"):
        return entry["host_template"].format(region=region)
    if entry.get("host"):
        return entry["host"]
    return env("VOLCENGINE_ENDPOINT") or DEFAULT_HOST


def registry_by_name(include_test: bool = False) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in API_REGISTRY:
        if entry.get("test_only") and not include_test:
            continue
        index.setdefault(entry["name"], []).append(entry)
    return index


def resolve_api(api_name: str, service: str | None, include_test: bool = False) -> dict[str, Any]:
    matches = registry_by_name(include_test).get(api_name, [])
    if service:
        matches = [entry for entry in matches if entry["service"] == service]
    if not matches:
        raise SystemExit(f"Unknown APIName: {api_name}. Use --list to inspect supported extension APIs.")
    if len(matches) > 1:
        services = ", ".join(sorted({entry["service"] for entry in matches}))
        raise SystemExit(f"APIName {api_name} is ambiguous across services: {services}. Pass --service.")
    return matches[0]


def action_kind(action: str) -> str:
    destructive_prefixes = ("Delete", "Terminate", "Release", "Revoke", "Modify", "Stop", "Detach", "Cancel")
    write_prefixes = ("Create", "Run", "Allocate", "Attach", "Associate", "Authorize", "Update", "Set", "Start", "Register", "Import")
    readonly_prefixes = ("Describe", "List", "Get", "Query", "Check", "Search")
    if action.startswith(destructive_prefixes):
        return "destructive"
    if action.startswith(write_prefixes):
        return "write"
    if action.startswith(readonly_prefixes):
        return "read"
    return "unknown"


def print_list(include_test: bool = False) -> None:
    entries = [entry for entry in API_REGISTRY if include_test or not entry.get("test_only")]
    for entry in sorted(entries, key=lambda e: (e["service"], e["name"])):
        print(
            f"{entry['name']}\t{entry['service']}\t{entry['version']}\t"
            f"{entry['method']}\t{entry.get('summary', '')}"
        )


def print_describe(entry: dict[str, Any]) -> None:
    print(json.dumps(entry, ensure_ascii=False, indent=2))


def call_api(args: argparse.Namespace) -> int:
    entry = resolve_api(args.api_name, args.service, include_test=args.include_test)
    expected_method = entry["method"].upper()
    if args.method and args.method.upper() != expected_method:
        raise SystemExit(f"{entry['name']} uses method {expected_method}, not {args.method.upper()}")

    params = parse_json_value(args.params)
    query_params, body_params = split_query_body(params, entry.get("query_keys"), entry.get("preserve_query_keys_in_body"))
    region = args.region or entry.get("region") or env("VOLCENGINE_REGION") or DEFAULT_REGION
    session_token = args.session_token or env("VOLCENGINE_SESSION_TOKEN")
    host = resolve_host(entry, region, args.host)
    scheme = args.scheme or entry.get("scheme") or "https"
    content_type = args.content_type or entry.get("content_type") or "application/json"

    ak = env("VOLCENGINE_ACCESS_KEY")
    sk = env("VOLCENGINE_SECRET_KEY")
    if not ak or not sk:
        raise SystemExit("VOLCENGINE_ACCESS_KEY and VOLCENGINE_SECRET_KEY are required")

    info = create_universal_info(
        service=entry["service"],
        action=entry["name"],
            version=entry["version"],
            method=expected_method,
            content_type=content_type,
        )
    client = create_api_client(ak=ak, sk=sk, session_token=session_token, region=region, host=host, scheme=scheme)
    if entry.get("call_style") == "flink_path":
        response, status_code, response_headers = call_flink_path(
            ak=ak,
            sk=sk,
            session_token=session_token,
            region=region,
            host=host,
            service=entry["service"],
            version=entry["version"],
            action=entry["name"],
            method=expected_method,
            content_type=content_type,
            params=params,
            query_keys=entry.get("query_keys"),
            preserve_query_keys_in_body=entry.get("preserve_query_keys_in_body"),
            scheme=scheme,
        )
    elif query_params and expected_method == "POST":
        response, status_code, response_headers = signed_post_with_query(
            ak=ak,
            sk=sk,
            session_token=session_token,
            region=region,
            host=host,
            service=entry["service"],
            version=entry["version"],
            action=entry["name"],
            content_type=content_type,
            query=query_params,
            body=body_params,
            scheme=scheme,
        )
    elif entry.get("call_style") == "action_version":
        response, status_code, response_headers = signed_action_version_request(
            ak=ak,
            sk=sk,
            session_token=session_token,
            region=region,
            host=host,
            service=entry["service"],
            version=entry["version"],
            action=entry["name"],
            method=expected_method,
            content_type=content_type,
            query=query_params,
            body=body_params,
            scheme=scheme,
        )
    else:
        response, status_code, response_headers = client.do_call_with_http_info(info=info, body=params)

    if args.output == "json":
        print(json.dumps(response, ensure_ascii=False))
    else:
        print(f"Status Code: {status_code}")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        if args.show_headers:
            print("Response Headers:")
            print(json.dumps(dict(response_headers), ensure_ascii=False, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call Volcengine extension APIs")
    parser.add_argument("--api", "--api-name", dest="api_name", help="APIName/Action to call")
    parser.add_argument("--params", "--param", default="{}", help="JSON object or @file.json, default {}")
    parser.add_argument("--method", choices=["GET", "POST", "get", "post"], help="Optional method assertion")
    parser.add_argument("--service", help="ServiceCode disambiguator for duplicate API names")
    parser.add_argument("--region", help="Request region, default VOLCENGINE_REGION or cn-beijing")
    parser.add_argument("--host", help="Override endpoint host; otherwise uses the registry host or VOLCENGINE_ENDPOINT fallback")
    parser.add_argument("--scheme", choices=["https", "http"], help="Override endpoint scheme")
    parser.add_argument("--content-type", help="Override content type")
    parser.add_argument("--session-token", help="Override VOLCENGINE_SESSION_TOKEN")
    parser.add_argument("--output", choices=["pretty", "json"], default="pretty")
    parser.add_argument("--show-headers", action="store_true")
    parser.add_argument("--include-test", action="store_true", help="Include test-only APIs in --list/--describe/calls")
    parser.add_argument("--list", action="store_true", help="List supported extension APIs")
    parser.add_argument("--describe", metavar="APIName", help="Print registry metadata for an API")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        print_list(include_test=args.include_test)
        return 0
    if args.describe:
        print_describe(resolve_api(args.describe, args.service, include_test=args.include_test))
        return 0
    if not args.api_name:
        parser.error("--api is required unless --list or --describe is used")
    return call_api(args)


if __name__ == "__main__":
    raise SystemExit(main())
