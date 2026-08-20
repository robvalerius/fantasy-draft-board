"""One-time OAuth authorization. Run: python auth.py"""

from urllib.parse import parse_qs, urlparse

from yahoo_client import build_authorize_url, exchange_code

print("\n1. Open this URL in your browser and click Agree:\n")
print(build_authorize_url())
print("\n2. You'll land on a 404 page. Copy the FULL address bar URL.\n")

pasted = input("Paste it here: ").strip()

if "code=" in pasted:
    code = parse_qs(urlparse(pasted).query)["code"][0]
else:
    code = pasted

exchange_code(code)
print("\nAuthorized. tokens.json saved -- refreshes automatically from now on.")
