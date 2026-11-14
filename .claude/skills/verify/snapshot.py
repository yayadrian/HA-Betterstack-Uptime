"""Print this integration's entities (registry + live state) and devices via HA's websocket API."""
import asyncio, json, sys
import aiohttp

async def main(token):
    async with aiohttp.ClientSession() as s, s.ws_connect("http://127.0.0.1:18123/api/websocket") as ws:
        await ws.receive_json(); await ws.send_json({"type": "auth", "access_token": token}); await ws.receive_json()
        async def call(i, t, **kw):
            await ws.send_json({"id": i, "type": t, **kw}); return (await ws.receive_json())["result"]
        ents = [e for e in await call(1, "config/entity_registry/list") if e["platform"] == "betterstack_uptime"]
        devs = {d["id"]: d for d in await call(2, "config/device_registry/list")}
        states = {st["entity_id"]: st for st in await call(3, "get_states")}
        for e in sorted(ents, key=lambda e: e["unique_id"]):
            st = states.get(e["entity_id"])
            d = devs.get(e["device_id"]) or {}
            print(f'{e["unique_id"]:22} {e["entity_id"]:42} state={st["state"] if st else "<no state>":12} '
                  f'class={(st or {}).get("attributes", {}).get("device_class")} device={d.get("name")!r}/{d.get("model")!r} ids={d.get("identifiers")}')
            if st and e["entity_id"].startswith("binary_sensor"):
                print("    attrs:", {k: v for k, v in st["attributes"].items() if k not in ("friendly_name",)})

asyncio.run(main(open(sys.argv[1]).read().strip()))
