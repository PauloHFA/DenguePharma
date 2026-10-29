"""Cliente do dashboard sem token, cache global ou acesso direto ao banco legado."""
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen, Request


def base_url(): return os.getenv("ANALYTICS_API_URL", "http://127.0.0.1:18081").rstrip("/")


def get(path):
    with urlopen(base_url()+path, timeout=30) as response: return json.load(response)


def private(path, *, token=None, data=None, raw=None, binary=False):
    if data is not None and raw is not None: raise ValueError("MULTIPLE_REQUEST_BODIES")
    headers={"Content-Type":"text/csv" if raw is not None else "application/json"}
    if token: headers["Authorization"]="Bearer "+token
    request=Request(base_url()+"/api/clinical"+path,headers=headers,data=json.dumps(data).encode() if data is not None else raw)
    with urlopen(request,timeout=30) as response: return response.read() if binary else json.load(response)


def table(run_id, name, *, offset=0, limit=100, **filters):
    query = urlencode({"offset": offset, "limit": limit, **{k: v for k,v in filters.items() if v}})
    return get(f"/api/public/analyses/{run_id}/tables/{name}?{query}")
