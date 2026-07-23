import requests
import re
import os
import json

TXT_DOSYASI = "kanallar.txt"

def extract_live_ids_from_json(data):
    """
    YouTube JSON ağacında özyinelemeli (recursive) olarak dolaşır
    ve canlı yayın olan tüm videoId değerlerini toplar.
    """
    found_ids = []

    def recursive_search(item):
        if isinstance(item, dict):
            # Eğer obje bir video renderer bloğu ise ve canlı yayın rozeti/bilgisi barındırıyorsa
            if "videoId" in item:
                item_str = json.dumps(item)
                # YouTube'un canlı yayın belirteçleri
                if any(badge in item_str for badge in [
                    "BADGE_STYLE_TYPE_LIVE_NOW", 
                    '"style":"LIVE"', 
                    '"text":"CANLI"', 
                    '"text":"LIVE"',
                    "LIVE_NOW"
                ]):
                    found_ids.append(item["videoId"])
            
            for v in item.values():
                recursive_search(v)
        elif isinstance(item, list):
            for element in item:
                recursive_search(element)

    recursive_search(data)
    return found_ids

def get_channel_live_ids(kanal_adi):
    url = f"https://www.youtube.com/@{kanal_adi}/streams"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
    }
    
    found_ids = []
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        # 1. YÖNTEM: ytInitialData JSON objesini çıkar ve ağaç olarak tara
        json_match = re.search(r'var ytInitialData\s*=\s*({.*?});</script>', r.text)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                found_ids = extract_live_ids_from_json(data)
            except Exception as e:
                print(f"  └─ JSON ayrıştırma hatası: {e}")

        # 2. YÖNTEM: Eğer JSON'dan gelmediyse ham HTML regex taraması
        if not found_ids:
            found_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?BADGE_STYLE_TYPE_LIVE_NOW', r.text)

        # 3. YÖNTEM: Doğrudan /live yönlendirme kontrolü (Son çare)
        if not found_ids:
            r_live = requests.get(f"https://www.youtube.com/@{kanal_adi}/live", headers=headers, timeout=15)
            canonical = re.search(r'<link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">', r_live.text)
            if canonical:
                found_ids.append(canonical.group(1))

        # Tekrar eden ID'leri sırasını bozmadan temizle
        unique_ids = list(dict.fromkeys(found_ids))
        return unique_ids

    except Exception as e:
        print(f"  └─ [{kanal_adi}] Bağlantı hatası: {e}")
        return []

def process_all_channels():
    if not os.path.exists(TXT_DOSYASI):
        print(f"Hata: '{TXT_DOSYASI}' dosyası bulunamadı!")
        return

    with open(TXT_DOSYASI, "r", encoding="utf-8") as f:
        satirlar = f.readlines()

    islenen_kanallar = set()
    yeni_satirlar = []
    degisiklik_var_mi = False

    for satir in satirlar:
        satir_clean = satir.strip()
        
        if not satir_clean or satir_clean.startswith("#") or "|" not in satir_clean:
            yeni_satirlar.append(satir)
            continue

        ham_kanal, mevcut_id = satir_clean.split("|", 1)
        kok_kanal = ham_kanal.split("_")[0].strip()

        if kok_kanal in islenen_kanallar:
            continue

        islenen_kanallar.add(kok_kanal)
        print(f"[Taraniyor] -> {kok_kanal}")
        
        live_ids = get_channel_live_ids(kok_kanal)

        if live_ids:
            print(f"  └─ Aktif Yayın Sayısı: {len(live_ids)}")
            for index, v_id in enumerate(live_ids, start=1):
                etiket = f"{kok_kanal}_{index}" if len(live_ids) > 1 else kok_kanal
                yeni_satir = f"{etiket}|{v_id}\n"
                
                yeni_satirlar.append(yeni_satir)
                print(f"     └─ {etiket} -> {v_id}")
                degisiklik_var_mi = True
        else:
            print("  └─ Aktif canlı yayın bulunamadı. Eski satır korundu.")
            yeni_satirlar.append(satir)

    if degisiklik_var_mi:
        with open(TXT_DOSYASI, "w", encoding="utf-8") as f:
            f.writelines(yeni_satirlar)
        print("\n'kanallar.txt' başarıyla güncellendi!")

if __name__ == "__main__":
    process_all_channels()
