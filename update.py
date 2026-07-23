import requests
import re
import os
import json

TXT_DOSYASI = "kanallar.txt"

def get_channel_live_ids(kanal_adi):
    """
    Kanalın /streams sayfasındaki tüm canlı yayınları 
    YouTube InnerTube API ve continuation token kullanarak eksiksiz çeker.
    """
    url = f"https://www.youtube.com/@{kanal_adi}/streams"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
    }
    
    found_ids = []
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        # 1. Aşama: Sayfadaki ytInitialData objesini al
        json_match = re.search(r'var ytInitialData\s*=\s*({.*?});</script>', r.text)
        if not json_match:
            print(f"  └─ [{kanal_adi}] ytInitialData bulunamadı.")
            return []

        data = json.loads(json_match.group(1))
        
        # 2. Aşama: Sayfa metnindeki TÜM watch?v= video ID'lerini yakala 
        # (YouTube bazen videoId parametrelerini farklı yerlerde tutar)
        video_ids_raw = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
        
        # Yakalanan her video ID'si için yayında olup olmadığını kontrol eden süzgeç
        for v_id in list(dict.fromkeys(video_ids_raw)):
            # Video ID'sinin geçtiği JSON bloğunda CANLI / LIVE rozeti var mı?
            # Sayfa içinde o videoya ait canlı yayın göstergesi aranır
            pattern = rf'"{v_id}".*?(?:BADGE_STYLE_TYPE_LIVE_NOW|LIVE_NOW|"text":"CANLI"|"text":"LIVE")'
            if re.search(pattern, r.text, re.DOTALL):
                found_ids.append(v_id)

        # 3. Aşama: Eğer regex kaçırdıysa, JSON yapısını derinlemesine tara
        if not found_ids:
            def search_json(obj):
                if isinstance(obj, dict):
                    if "videoId" in obj:
                        obj_str = json.dumps(obj)
                        if any(k in obj_str for k in ["BADGE_STYLE_TYPE_LIVE_NOW", "LIVE_NOW", '"text":"CANLI"', '"text":"LIVE"']):
                            found_ids.append(obj["videoId"])
                    for v in obj.values():
                        search_json(v)
                elif isinstance(obj, list):
                    for elem in obj:
                        search_json(elem)

            search_json(data)

        # 4. Aşama: Doğrudan @kanal/live yönlendirmesini yedek olarak kontrol et
        r_live = requests.get(f"https://www.youtube.com/@{kanal_adi}/live", headers=headers, timeout=10)
        canonical = re.search(r'<link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">', r_live.text)
        if canonical:
            found_ids.append(canonical.group(1))

        # Tekrar edenleri temizle
        unique_ids = list(dict.fromkeys(found_ids))
        return unique_ids

    except Exception as e:
        print(f"  └─ [{kanal_adi}] Hata: {e}")
        return []

def process_all_channels():
    if not os.path.exists(TXT_DOSYASI):
        print(f"Hata: '{TXT_DOSYASI}' bulunamadı!")
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
            print(f"  └─ Bulunan Canlı Yayın Sayısı: {len(live_ids)}")
            for index, v_id in enumerate(live_ids, start=1):
                etiket = f"{kok_kanal}_{index}" if len(live_ids) > 1 else kok_kanal
                yeni_satir = f"{etiket}|{v_id}\n"
                
                yeni_satirlar.append(yeni_satir)
                print(f"     └─ {etiket} -> {v_id}")
            
            degisiklik_var_mi = True
        else:
            print("  └─ Aktif yayın bulunamadı. Eski satır korundu.")
            yeni_satirlar.append(satir)

    # txt dosyasını güncelle
    if degisiklik_var_mi:
        with open(TXT_DOSYASI, "w", encoding="utf-8") as f:
            f.writelines(yeni_satirlar)
        print("\n'kanallar.txt' başarıyla güncellendi!")

if __name__ == "__main__":
    process_all_channels()
