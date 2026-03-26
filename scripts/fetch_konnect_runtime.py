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

# Try to get PAT from environment, else fallback to hardcoded POC token for the demo
KONG_PAT = os.environ.get("KONG_PAT", "kpat_zMYwMTvjEynkhHtm23MYvwz7qrF9X0qQnqfecgMo30bwWS1xq")
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
            
            # Mocking analytics for now (unless we integrate the analytics V2 API which takes time)
            # In a real holy-grail enterprise dashboard, we would query the `/v2/control-planes/{cp_id}/analytics` endpoint
            mock_traffic = 5000 if svc_name == "poc-api-1" else 15000
            
            # Identify Security Rating based on plugins
            is_secure = "key-auth" in plugins or "oidc" in plugins or "jwt" in plugins
            
            results[svc_name] = {
                "kong_runtime_status": "Active" if len(plugins) > 0 else "Inactive",
                "kong_plugins": plugins,
                "kong_is_secure": is_secure,
                "kong_thirty_day_traffic": mock_traffic
            }
            
            print(f" -> Fetched Runtime for {svc_name}: {len(plugins)} plugins")
            
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
