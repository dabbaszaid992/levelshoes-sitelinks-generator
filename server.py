"""
Level Shoes Sitelinks Generator — Local AI Server
Run: py server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os, json

# ══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — fill in your credentials
# ══════════════════════════════════════════════════════════════════════════

OPENAI_API_KEY         = "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"

GOOGLE_DEVELOPER_TOKEN = "gu9dA36n36VdJvr25vTdFg"
GOOGLE_CLIENT_ID       = "188519388533-rh6bll4jknob3u4cgjba6uf2oni55j7u.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET   = "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"
GOOGLE_REFRESH_TOKEN   = "1//0ga-8LZexoSOICgYIARAAGBASNwF-L9Ir26kzMMkfvO8LGDP0O7O-cctZsxAOaQnisukG97SryNr-EczA2KpQQMGso59bURZcWxY"
MCC_CUSTOMER_ID        = "162-305-8174"   # Your MCC account ID (with dashes)

# ══════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
DEFAULT_MODEL = "gpt-4o"


# ── OpenAI ─────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "model_default": DEFAULT_MODEL}


@app.route("/generate", methods=["POST"])
def generate():
    data   = request.get_json()
    prompt = data.get("prompt", "")
    model  = data.get("model", DEFAULT_MODEL)
    if not prompt:
        return {"error": "No prompt"}, 400
    try:
        response = openai_client.chat.completions.create(
            model=model, max_tokens=2000, temperature=0.8,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"result": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}, 500


# ── Google Ads helpers ─────────────────────────────────────────────────────
def get_access_token():
    import urllib.request, urllib.parse
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN, "grant_type": "refresh_token",
    }).encode()
    req  = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["access_token"]


def ads_headers(access_token, cid):
    return {
        "Authorization":     f"Bearer {access_token}",
        "developer-token":   GOOGLE_DEVELOPER_TOKEN,
        "login-customer-id": MCC_CUSTOMER_ID.replace("-", ""),
        "Content-Type":      "application/json",
    }


def ads_request(url, body, access_token, cid):
    import urllib.request
    headers = ads_headers(access_token, cid)
    full_url = url.replace("{cid}", cid)
    req = urllib.request.Request(full_url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode()}"


# ── Debug endpoint — shows exact Google error ──────────────────────────────
@app.route("/gads/debug", methods=["GET"])
def gads_debug():
    import urllib.request, urllib.error
    try:
        token  = get_access_token()
        mcc_id = MCC_CUSTOMER_ID.replace("-", "")
        print(f"\n[DEBUG] MCC ID (no dashes): {mcc_id}")
        print(f"[DEBUG] Developer Token: {GOOGLE_DEVELOPER_TOKEN[:8]}...")
        print(f"[DEBUG] Access token obtained: {token[:20]}...")

        headers = ads_headers(token, mcc_id)
        url  = f"https://googleads.googleapis.com/v17/customers/{mcc_id}/googleAds:searchStream"
        body = {"query": "SELECT customer_client.id, customer_client.descriptive_name, customer_client.currency_code, customer_client.manager, customer_client.status FROM customer_client WHERE customer_client.status = 'ENABLED'"}

        print(f"[DEBUG] Calling URL: {url}")
        req  = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req)
            raw  = json.loads(resp.read())
            print(f"[DEBUG] SUCCESS! Raw response keys: {[list(b.keys()) for b in raw[:1]]}")
            return jsonify({"status": "success", "raw_sample": raw[:1]})
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            print(f"[DEBUG] HTTP {e.code} ERROR: {err_body}")
            return jsonify({
                "http_code": e.code,
                "error_detail": json.loads(err_body) if err_body.startswith("{") else err_body,
                "mcc_id_used": mcc_id,
                "url_called": url,
            }), 400
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[DEBUG] Exception: {tb}")
        return jsonify({"error": str(e), "trace": tb}), 500


# ── List accessible accounts under MCC ────────────────────────────────────
@app.route("/gads/accounts", methods=["GET"])
def gads_accounts():
    import urllib.request, urllib.error
    try:
        token  = get_access_token()
        mcc_id = MCC_CUSTOMER_ID.replace("-", "")
        headers = ads_headers(token, mcc_id)

        url  = f"https://googleads.googleapis.com/v17/customers/{mcc_id}/googleAds:searchStream"
        body = {"query": "SELECT customer_client.id, customer_client.descriptive_name, customer_client.currency_code, customer_client.time_zone, customer_client.manager, customer_client.status FROM customer_client WHERE customer_client.status = 'ENABLED'"}

        req  = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req)
            raw  = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            print(f"[ACCOUNTS ERROR] HTTP {e.code}: {err_body}")
            try:
                err_json = json.loads(err_body)
                msg = err_json.get("error", {}).get("message") or err_body
            except:
                msg = err_body
            return jsonify({"error": msg, "http_code": e.code, "mcc_id": mcc_id}), 400

        accounts = []
        for batch in raw:
            for row in batch.get("results", []):
                c = row.get("customerClient", {})
                if not c.get("manager", False):
                    accounts.append({
                        "id":       c.get("id"),
                        "name":     c.get("descriptiveName", "—"),
                        "currency": c.get("currencyCode", ""),
                        "timezone": c.get("timeZone", ""),
                    })
        return jsonify({"accounts": sorted(accounts, key=lambda x: x["name"])})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ── List campaigns for a given account ────────────────────────────────────
@app.route("/gads/campaigns", methods=["POST"])
def gads_campaigns():
    data        = request.get_json()
    customer_id = data.get("customer_id", "").replace("-", "")
    if not customer_id:
        return jsonify({"error": "customer_id required"}), 400
    try:
        token   = get_access_token()
        headers = ads_headers(token, customer_id)
        import urllib.request
        url  = f"https://googleads.googleapis.com/v17/customers/{customer_id}/googleAds:searchStream"
        body = {"query": "SELECT campaign.id, campaign.name, campaign.status FROM campaign WHERE campaign.status IN ('ENABLED','PAUSED') ORDER BY campaign.name"}
        req  = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        resp = urllib.request.urlopen(req)
        raw  = json.loads(resp.read())
        campaigns = []
        for batch in raw:
            for row in batch.get("results", []):
                c = row.get("campaign", {})
                campaigns.append({"id": c.get("id"), "name": c.get("name"), "status": c.get("status")})
        return jsonify({"campaigns": campaigns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Push sitelinks to specific campaigns ──────────────────────────────────
@app.route("/gads/push-sitelinks", methods=["POST"])
def push_sitelinks():
    """
    Body: {
      "customer_id": "123-456-7890",
      "campaign_ids": ["111", "222"],
      "sitelinks": [{"sl":"...", "d1":"...", "d2":"...", "url":"..."}]
    }
    """
    data         = request.get_json()
    customer_id  = data.get("customer_id", "").replace("-", "")
    campaign_ids = data.get("campaign_ids", [])
    sitelinks    = data.get("sitelinks", [])

    if not customer_id:  return jsonify({"error": "customer_id required"}), 400
    if not campaign_ids: return jsonify({"error": "Select at least one campaign"}), 400
    if not sitelinks:    return jsonify({"error": "No sitelinks provided"}), 400

    try:
        import urllib.request
        token   = get_access_token()
        headers = ads_headers(token, customer_id)
        mutate_url = f"https://googleads.googleapis.com/v17/customers/{customer_id}/googleAds:mutate"
        results = {"created": 0, "linked": 0, "errors": []}
        asset_rns = []

        # Step 1: Create sitelink assets
        ops = [{"assetOperation": {"create": {"sitelinkAsset": {
            "linkText": sl["sl"][:25], "description1": sl["d1"][:35],
            "description2": sl["d2"][:35], "finalUrls": [sl["url"]],
        }}}} for sl in sitelinks]

        req = urllib.request.Request(mutate_url, data=json.dumps({"mutateOperations": ops}).encode(), headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req)
            for r in json.loads(resp.read()).get("mutateOperationResponses", []):
                rn = r.get("assetResult", {}).get("resourceName")
                if rn:
                    asset_rns.append(rn)
                    results["created"] += 1
        except urllib.error.HTTPError as e:
            results["errors"].append(f"Asset creation: {e.read().decode()}")
            return jsonify(results), 400

        # Step 2: Link assets to campaigns
        link_ops = [
            {"campaignAssetOperation": {"create": {
                "campaign": f"customers/{customer_id}/campaigns/{cid}",
                "asset": rn, "fieldType": "SITELINK",
            }}}
            for cid in campaign_ids for rn in asset_rns
        ]
        if link_ops:
            req2 = urllib.request.Request(mutate_url, data=json.dumps({"mutateOperations": link_ops}).encode(), headers=headers, method="POST")
            try:
                resp2 = urllib.request.urlopen(req2)
                results["linked"] = len(json.loads(resp2.read()).get("mutateOperationResponses", []))
            except urllib.error.HTTPError as e:
                results["errors"].append(f"Campaign linking: {e.read().decode()}")

        results["message"] = f"✅ {results['created']} sitelinks created & linked to {len(campaign_ids)} campaign(s)"
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── OAuth2 setup helpers (run once to get refresh token) ──────────────────
@app.route("/gads/auth-url", methods=["GET"])
def auth_url():
    import urllib.parse
    url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID, "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "response_type": "code", "scope": "https://www.googleapis.com/auth/adwords",
        "access_type": "offline", "prompt": "consent",
    })
    return jsonify({"auth_url": url, "step": "1. Visit this URL and authorize. 2. Copy the code. 3. POST it to /gads/auth-token"})


@app.route("/gads/auth-token", methods=["POST"])
def auth_token():
    import urllib.request, urllib.parse
    code = request.get_json().get("code", "")
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code, "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code",
    }).encode()
    req  = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    return jsonify({"refresh_token": data.get("refresh_token"),
                    "next": "Paste this refresh_token into GOOGLE_REFRESH_TOKEN in server.py and restart"})


if __name__ == "__main__":
    print("\n✅ Level Shoes Server running!")
    print("🤖 GPT-4o | 📊 Google Ads API v17")
    print("🌐 Open the HTML file in your browser\n")
    print("── First-time Google Ads setup ──────────────────")
    print("1. Fill in all 5 credentials at the top of server.py")
    print("2. GET  http://localhost:5000/gads/auth-url")
    print("3. Visit the URL, authorize, copy the code")
    print("4. POST http://localhost:5000/gads/auth-token  {\"code\":\"...\"}")
    print("5. Copy refresh_token → paste into GOOGLE_REFRESH_TOKEN above")
    print("6. Restart server — you're connected!\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

