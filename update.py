import requests
import re
import os
import json

TXT_DOSYASI = "kanallar.txt"

def get_channel_live_ids(kanal_adi):
    """
    Kanalın /streams sayfasındaki JavaScript verilerini (ytInitialData) 
    ayrıştırarak AKTİF olan tüm canlı yayın ID'lerini bulur.
    """
    url = f"https://www.youtube.com/@{kanal_adi}/streams"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
    }
    
    found_ids = []
    
    try:
        r = requests.get(url, headers=headers, timeout=12)
        
        # 1. YÖNTEM: YouTube'un ytInitialData JSON objesinden 'CANLI/LIVE' olanları tara
        json_match = re.search(r'var ytInitialData = ({.*?});</script>', r.text)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                # JSON metninde geçen tüm videoId ve overlay/label yapılarını string olarak tara
                json_str = json.dumps(data)
                
                # "style":"LIVE"` veya `"label":"CANLI"` / `"label":"LIVE"` içeren video render bloklarını yakala
                live_blocks = re.findall(r'{"videoId":"([a-zA-Z0-9_-]{11})".*?(?:LIVE|CANLI)', json_str)
                found_ids.extend(live_blocks)
            except Exception:
                pass

        # 2. YÖNTEM: Sayfa ham metninden canlı yayın rozeti içeren videoId'leri regex ile tara (Yedek)
        if not found_ids:
            raw_matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"[^}]{0,300}?(?:style":"LIVE"|label":"CANLI")', r.text)
            found_ids.extend(raw_matches)

        # 3. YÖNTEM: Özel yönlendirme /live link kontrolü
        if not found_ids:
            r_live = requests.get(f"https://www.youtube.com/@{kanal_adi}/live", headers=headers, timeout=12)
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
        # Eğer kanalda önceden eklenmiş _1, _2 eki varsa temizleyip kök kanal adını alır
        kok_kanal = ham_kanal.split("_")[0].strip()

        if kok_kanal in islenen_kanallar:
            # Bu kanal zaten yukarıda işlendiği için eski alt yayın satırlarını atlar
            continue

        islenen_kanallar.add(kok_kanal)
        print(f"[Taraniyor] -> {kok_kanal}")
        
        live_ids = get_channel_live_ids(kok_kanal)

        if live_ids:
            print(f"  └─ Aktif Yayın Sayısı: {len(live_ids)}")
            for index, v_id in enumerate(live_ids, start=1):
                # Kanalın 1 tane yayını varsa: NostaljiTRT|ID
                # Kanalın 2 veya daha çok yayını varsa: NostaljiTRT_1|ID1, NostaljiTRT_2|ID2
                etiket = f"{kok_kanal}_{index}" if len(live_ids) > 1 else kok_kanal
                yeni_satir = f"{etiket}|{v_id}\n"
                
                yeni_satirlar.append(yeni_satir)
                print(f"     └─ {etiket} -> {v_id}")
                degisiklik_var_mi = True
        else:
            print("  └─ Aktif canlı yayın bulunamadı. Eski satır korundu.")
            yeni_satirlar.append(satir)

    # txt dosyasını güncelle
    if degisiklik_var_mi:
        with open(TXT_DOSYASI, "w", encoding="utf-8") as f:
            f.writelines(yeni_satirlar)
        print("\n'kanallar.txt' başarıyla güncellendi!")

if __name__ == "__main__":
    process_all_channels()
