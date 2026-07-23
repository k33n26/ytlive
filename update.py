import subprocess
import json
import os

TXT_DOSYASI = "kanallar.txt"

def get_channel_live_ids(kanal_adi):
    """
    yt-dlp kullanarak kanalın canlı yayınlar sekmesindeki 
    AKTİF tüm canlı yayın ID'lerini çek
    """
    url = f"https://www.youtube.com/@{kanal_adi}/streams"
    
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--playlist-items", "1-10",
        url
    ]
    
    found_ids = []
    
    try:
        # Hata veren text=encoding satırı burada düzeltildi: text=True, encoding="utf-8"
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            entries = data.get("entries", [])
            
            for entry in entries:
                is_live = entry.get("is_live")
                live_status = entry.get("live_status")
                
                if is_live is True or live_status == "is_live":
                    v_id = entry.get("id")
                    if v_id:
                        found_ids.append(v_id)
                        
    except Exception as e:
        print(f"  └─ [{kanal_adi}] yt-dlp hatası: {e}")

    # Eğer /streams sekmesinden yakalayamazsa doğrudan /live yönlendirmesini dene
    if not found_ids:
        cmd_fallback = ["yt-dlp", "--get-id", f"https://www.youtube.com/@{kanal_adi}/live"]
        try:
            res_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, encoding="utf-8", timeout=15)
            if res_fb.returncode == 0 and res_fb.stdout.strip():
                found_ids.append(res_fb.stdout.strip())
        except Exception:
            pass

    return list(dict.fromkeys(found_ids))

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

    if degisiklik_var_mi:
        with open(TXT_DOSYASI, "w", encoding="utf-8") as f:
            f.writelines(yeni_satirlar)
        print("\n'kanallar.txt' başarıyla güncellendi!")

if __name__ == "__main__":
    process_all_channels()
