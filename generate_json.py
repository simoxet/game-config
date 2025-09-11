import json

data = {
    "QuickDownload": "true",
    "QuickDownloadURL": "amzn://apps/android?initiatePurchaseFlow=true&asin=B0DPTMRBZY"
}

for i in range(41, 101):
    with open(f"{i}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
