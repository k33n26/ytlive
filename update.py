import requests
import re
import os

TXT_DOSYASI = "kanallar.txt"

def get_channel_live_ids(kanal_adi):
    """
    Kanalın canlı yayın/streams sayfasını tarayarak aktif TÜM canlı yayın ID'lerini döndürür.
    """
    url = f"https://www.youtube.com/@{kanal_adi}/streams"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            # Alternatif olarak direkt /live adresini dene
            r = requests.get(f"https://www.youtube.com/@{kanal_adi}/live", headers=headers, timeout=12)

        # YouTube sayfasındaki aktif canlı yayın video ID'lerini yakala
        # 'LIVE' ibaresi içeren video bloklarını arar
        found_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"style":"LIVE"', r.text)
        
        # Eğer özel regex eşleşmezse standart canonical/watch regex'i kullan
        if not found_ids:
            found_ids = re.findall(r'<link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">', r.text)

        # Tekrar eden ID'leri temizle (Sırasını koruyarak)
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

    # Mevcut kanalların listesini çıkar (Tekrarları önlemek için)
    islenen_kanallar = set()
    yeni_satirlar = []
    degisiklik_var_mi = False

    for satir in satirlar:
        satir_clean = satir.strip()
        
        # Boş satırları veya yorum satırlarını koru
        if not satir_clean or satir_clean.startswith("#") or "|" not in satir_clean:
            yeni_satirlar.append(satir)
            continue

        # Ana kanal adını al (örneğin limonzeytin_1 geldiyse kök adı 'limonzeytin' yapar)
        ham_kanal, mevcut_id = satir_clean.split("|", 1)
        kok_kanal = ham_kanal.split("_")[0].strip()

        if kok_kanal in islenen_kanallar:
            # Bu kanal zaten yukarıda çoklu yayın olarak işlendi, eski alt satırı atla
            continue

        islenen_kanallar.add(kok_kanal)
        print(f"[Taraniyor] -> {kok_kanal}")
        
        live_ids = get_channel_live_ids(kok_kanal)

        if live_ids:
            print(f"  └─ Aktif Yayın Sayısı: {len(live_ids)}")
            for index, v_id in enumerate(live_ids, start=1):
                # Tek yayın varsa 'limonzeytin', birden fazla varsa 'limonzeytin_1', 'limonzeytin_2'
                etiket = f"{kok_kanal}_{index}" if len(live_ids) > 1 else kok_kanal
                yeni_satir = f"{etiket}|{v_id}\n"
                
                yeni_satirlar.append(yeni_satir)
                if v_id != mevcut_id:
                    degisiklik_var_mi = True
                    print(f"     └─ {etiket} -> Güncellendi: {v_id}")
                else:
                    print(f"     └─ {etiket} -> Değişiklik yok.")
        else:
            print("  └─ Aktif canlı yayın bulunamadı. Eski satır korundu.")
            yeni_satirlar.append(satir)

    # Güncellenmiş verileri txt dosyasına yaz
    with open(TXT_DOSYASI, "w", encoding="utf-8") as f:
        f.writelines(yeni_satirlar)

    print("\nİşlem tamamlandı.")

if __name__ == "__main__":
    process_all_channels()
