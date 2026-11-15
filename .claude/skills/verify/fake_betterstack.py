"""Fake Better Stack Uptime API. POST /admin {"heartbeats": "ok"|"403"|"500"|"gone"} switches mode."""
import json, sys
from aiohttp import web

PORT = int(sys.argv[1])
BASE = f"http://127.0.0.1:{PORT}/api/v2"
state = {"heartbeats": "ok"}
TOKEN = "good-token"

MONITORS = [
    {"id": "1", "attributes": {"pronounceable_name": "Website", "status": "up", "monitor_type": "status",
                               "url": "https://example.com", "last_checked_at": "2026-11-14T22:00:00Z"}},
]
# page 1 and page 2 to exercise pagination; heartbeat 1 collides with monitor 1
HB_PAGES = [
    [{"id": "1", "type": "heartbeat", "attributes": {"name": "Nightly Backup", "status": "up", "period": 86400,
      "grace": 300, "paused_at": None, "url": "https://uptime.betterstack.com/api/v1/heartbeat/SECRET1"}}],
    [{"id": "2", "type": "heartbeat", "attributes": {"name": None, "status": "down", "period": 3600,
      "grace": 60, "paused_at": None, "url": "https://uptime.betterstack.com/api/v1/heartbeat/SECRET2"}}],
]

def auth_ok(req):
    return req.headers.get("Authorization") == f"Bearer {TOKEN}"

async def monitors(req):
    if not auth_ok(req):
        return web.Response(status=401)
    return web.json_response({"data": MONITORS, "pagination": {"next": None}})

async def heartbeats(req):
    if not auth_ok(req):
        return web.Response(status=401)
    mode = state["heartbeats"]
    print("heartbeats request", req.query_string, "mode", mode, flush=True)
    if mode in ("403", "500"):
        return web.Response(status=int(mode))
    if mode == "gone":
        return web.json_response({"data": [], "pagination": {"next": None}})
    page = int(req.query.get("page", "1"))
    nxt = f"{BASE}/heartbeats?page={page + 1}" if page < len(HB_PAGES) else None
    return web.json_response({"data": HB_PAGES[page - 1], "pagination": {"next": nxt}})

async def admin(req):
    state.update(await req.json())
    print("admin", state, flush=True)
    return web.json_response(state)

app = web.Application()
app.add_routes([web.get("/api/v2/monitors", monitors), web.get("/api/v2/heartbeats", heartbeats), web.post("/admin", admin)])
web.run_app(app, host="127.0.0.1", port=PORT, print=None)
