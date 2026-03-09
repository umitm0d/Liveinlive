import json
import re
from cloudscraper import CloudScraper


class RecTVUrlFetcher:
    def __init__(self):
        self.session = CloudScraper()

    def get_rectv_domain(self):
        try:
            response = self.session.post(
                url="https://firebaseremoteconfig.googleapis.com/v1/projects/791583031279/namespaces/firebase:fetch",
                headers={
                    "X-Goog-Api-Key": "AIzaSyBbhpzG8Ecohu9yArfCO5tF13BQLhjLahc",
                    "X-Android-Package": "com.rectv.shot",
                    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)",
                },
                json={
                    "platformVersion": "25",
                    "appInstanceId": "fSrUnUPXQOCIN37mjVhnJo",
                    "packageName": "com.rectv.shot",
                    "appVersion": "19.3",
                    "countryCode": "TR",
                    "sdkVersion": "22.0.1",
                    "appBuild": "104",
                    "firstOpenTime": "2025-12-21T20:00:00.000Z",
                    "analyticsUserProperties": {},
                    "appId": "1:791583031279:android:244c3d507ab299fcabc01a",
                    "languageCode": "tr-TR",
                    "timeZone": "Africa/Nairobi"
                }
            )

            data = response.json()
            domains_str = data.get("entries", {}).get("ab_rotating_live_tv_domains", "[]")
            domains_list = json.loads(domains_str)

            # Domain al
            domain = domains_list[0] if domains_list else "cloudlyticsapp.lol"

            # HER ZAMAN HTTPS YAP
            domain = domain.replace("http://", "")
            domain = domain.replace("https://", "")
            domain = "https://" + domain.strip()

            print(f"✅ Güncel HTTPS domain: {domain}")
            return domain

        except Exception as e:
            print(f"❌ Domain alınamadı: {type(e).__name__} - {e}")
            return None

    def update_m3u_domains(self, m3u_file_path, new_domain):
        try:
            with open(m3u_file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Tüm http/https domainleri değiştir
            updated_content = re.sub(
                r'https?://[^/\s]+',
                new_domain,
                content
            )

            with open(m3u_file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)

            print("✅ M3U dosyası tamamen HTTPS domain ile güncellendi.")
            return True

        except Exception as e:
            print(f"❌ M3U güncellenemedi: {type(e).__name__} - {e}")
            return False


if __name__ == "__main__":
    fetcher = RecTVUrlFetcher()
    domain = fetcher.get_rectv_domain()

    if domain:
        fetcher.update_m3u_domains("r2.m3u", domain)
