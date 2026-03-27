import os
import urllib.request
import urllib.error
import json
import traceback

"""
Fetches live Runtime data from Kong Konnect Admin APIs.
Downloads:
- Number of active security plugins.
- Plugin types (rate-limiting, oidc, cors, etc).
- Health / Analytics (Mocked or queried depending on tier).
"""

# PAT must be provided via environment variable (GitHub Secret or local export)
KONG_PAT = os.environ.get("KONG_PAT", "")
if not KONG_PAT:
    print("⚠️  WARNING: KONG_PAT not set. Set it via: export KONG_PAT=kpat_...")
# Fixed to aez-dp-no-prod Control Plane for the POC
CP_ID = "6993903a-af80-4ead-9909-29f956e5d88e"
URL_BASE = f"https://eu.api.konghq.com/v2/control-planes/{CP_ID}/core-entities"

HEADERS = {
    "Authorization": f"Bearer {KONG_PAT}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def request(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} on GET {url}: {e.read().decode('utf-8')}")
        return {}

def fetch_kong_data():
    results = {}
    
    print("Fetching API Requests Analytics (last 7 days)...")
    analytics_counts = {}  # keyed by pure service_id
    total_fetched = 0
    MAX_PAGES = 50  # Safety cap: 50 pages × 1000 = 50,000 requests max
    try:
        req_url = "https://eu.api.konghq.com/v2/api-requests"
        cursor = None
        page = 0

        while page < MAX_PAGES:
            page += 1
            payload = {
                "size": 1000,
                "time_range": {"type": "relative", "time_range": "7D"}
            }
            if cursor:
                payload["cursor"] = cursor

            req_body = json.dumps(payload).encode("utf-8")
            req_obj = urllib.request.Request(req_url, data=req_body, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req_obj) as response:
                data = json.loads(response.read().decode("utf-8"))
                logs = data.get("results", [])
                meta = data.get("meta", {})

                for log in logs:
                    # gateway_service field contains "cp_id:service_id" composite key
                    raw_gw = log.get("gateway_service", "")
                    if not raw_gw:
                        continue
                    # Extract pure service_id (after the colon)
                    svc_id = raw_gw.split(":")[-1] if ":" in raw_gw else raw_gw
                    # response_http_status is a string like "200", "401", etc.
                    try:
                        status = int(log.get("response_http_status", "200"))
                    except (ValueError, TypeError):
                        status = 200
                    if svc_id not in analytics_counts:
                        analytics_counts[svc_id] = {"success": 0, "error": 0}
                    if status < 400:
                        analytics_counts[svc_id]["success"] += 1
                    else:
                        analytics_counts[svc_id]["error"] += 1

                total_fetched += len(logs)
                print(f" -> Page {page}: {len(logs)} requests fetched (total: {total_fetched})")

                # If fewer results than requested or no cursor → we've reached the end
                cursor = meta.get("cursor")
                if len(logs) < 1000 or not cursor:
                    break

        print(f" ✅ Aggregated {total_fetched} requests across {len(analytics_counts)} services.")
    except Exception as e:
        print(f"⚠️  Analytics fetch failed (non-blocking): {e}")
        
    print("Fetching services from Kong Konnect...")
    try:
        services_resp = request(f"{URL_BASE}/services")
        services = services_resp.get("data", [])
        
        for svc in services:
            svc_name = svc["name"]
            svc_id = svc["id"]
            
            # Fetch Plugins for this service
            pl_resp = request(f"{URL_BASE}/services/{svc_id}/plugins")
            plugins = [p["name"] for p in pl_resp.get("data", [])]
            
            # Fetch Real Traffic from aggregated memory
            ac = analytics_counts.get(svc_id, {"success": 0, "error": 0})
            real_traffic = f"{ac['success']} OK / {ac['error']} ERR"
            
            # Identify Security Rating based on plugins
            is_secure = "key-auth" in plugins or "oidc" in plugins or "jwt" in plugins
            
            results[svc_name] = {
                "kong_runtime_status": "Active" if len(plugins) > 0 else "Inactive",
                "kong_plugins": plugins,
                "kong_is_secure": is_secure,
                "kong_thirty_day_traffic": real_traffic
            }
            
            print(f" -> Fetched Runtime for {svc_name}: {len(plugins)} plugins | Traffic: {real_traffic}")
            
        # Write to JSON
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "kong_runtime.json")
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        print(f"✅ Successfully exported to {out_path}")

    except Exception as e:
        print("❌ Error fetching Kong Konnect runtime data:")
        traceback.print_exc()

if __name__ == "__main__":
    fetch_kong_data()
