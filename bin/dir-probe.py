#!/usr/bin/env python3
"""
Lightweight directory probe (corrective action 4).
Checks HTTP status codes of candidate directories before full submission.
Usage: python3 bin/dir-probe.py
"""
import subprocess, sys, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

URLS = {
    "TheAgentsIndex API": "https://theagentsindex.com/api/submit",
    "wmcp.sh home": "https://wmcp.sh/",
    "wmcp.sh directory": "https://wmcp.sh/directory",
    "wmcp.sh submit API": "https://wmcp.sh/api/v1/directory/submit",
    "SaaSCity MCP": "https://saascity.io/api/mcp",
    "AgentNDX": "https://agentndx.ai/",
    "AgentStore tools": "https://agentstore.tools/",
    "SubmitMap MCP": "https://submitmap.com/api/mcp",
    "SubmitMap llms": "https://submitmap.com/llms-full.txt",
    "Vend health": "https://extract.paypercall.dev/health",
    "McpServers.org": "https://mcpservers.org/servers/pandeveloper001/vend",
    "Influzer vend": "https://www.influzer.ai/mcp/vend-api-merchant",
    "AgentNDX vend": "https://agentndx.ai/server/vend",
    "BusinessMCP dir-submitter": "https://businessmcp.com/mcp-servers/free-directory-submitter",
}

def check(label, url):
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", f"%{{http_code}}", "--max-time", "10", url],
            capture_output=True, text=True, timeout=15
        )
        code = r.stdout.strip()
        if not code:
            return (label, url, "error", r.stderr.strip()[:80])
        return (label, url, code, "")
    except Exception as e:
        return (label, url, "exception", str(e)[:80])

results = []
with ThreadPoolExecutor(max_workers=10) as pool:
    fut = {pool.submit(check, label, url): label for label, url in URLS.items()}
    for f in as_completed(fut):
        results.append(f.result())

results.sort(key=lambda x: x[0])
print(json.dumps({
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "total": len(results),
    "results": [
        {"label": l, "url": u, "http": c if not e else c, "error": e}
        for l, u, c, e in results
    ]
}, indent=2))