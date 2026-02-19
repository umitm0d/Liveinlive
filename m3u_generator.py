#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🜲 ÜⲘ𝖎ţ KabloNet M3U & EPG Güncelleyici v2.2 (GitHub Secret Versiyonu)
Versiyon: 2.2
Tarih: 2024-06-20
GitHub Secret ile güvenli token kullanımı
"""

import os
import re
import json
import gzip
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime

# ---------------------------- GITHUB SECRET AYARLARI ----------------------------
# GitHub Secret'tan token'ları al
KABLO_TOKEN = os.environ.get('KABLO_TOKEN', '')
GRUP_EKI = os.environ.get('GRUP_EKI', '')  # Özel grup ön eki

# ---------------------------- SABIT AYARLAR ----------------------------
M3U_DOSYA_ADI = "1UmitTV.m3u"
EPG_DOSYA_ADI = "kabloepg.xml"
TEMEL_DIZIN = "."

API_URL = "https://core-api.kablowebtv.com/api/channels"
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Referer": "https://tvheryerde.com",
    "Origin": "https://tvheryerde.com",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip",
    "Authorization": f"Bearer {KABLO_TOKEN}"
}

# ---------------------------- RENKLİ YAZI FORMATLARI ----------------------------
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ---------------------------- YARDIMCI FONKSİYONLAR ----------------------------
def zaman_damgasi():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")

def baslik_yazdir():
    print(f"\n{bcolors.HEADER}{'═'*60}")
    print(f"{'🜲 ÜⲘ𝖎ţ KabloNet M3U & EPG Güncelleyici v2.2'.center(60)}")
    print(f"{'═'*60}{bcolors.ENDC}")
    print(f"{bcolors.BOLD}🔹 Çalışma Zamanı: {zaman_damgasi()}{bcolors.ENDC}")
    
    # Token kontrolü
    if KABLO_TOKEN:
        print(f"{bcolors.OKGREEN}🔑 KABLO_TOKEN: ✅ Mevcut{bcolors.ENDC}")
    else:
        print(f"{bcolors.FAIL}🔑 KABLO_TOKEN: ❌ BULUNAMADI!{bcolors.ENDC}")
    
    # Grup eki kontrolü
    if GRUP_EKI:
        print(f"{bcolors.OKGREEN}🔑 GRUP_EKI: ✅ Mevcut ({GRUP_EKI}){bcolors.ENDC}")
    else:
        print(f"{bcolors.WARNING}🔑 GRUP_EKI: ⚠️ Kullanılmıyor (boş){bcolors.ENDC}")
    
    print(f"{bcolors.OKBLUE}🔹 Çalışma Modu: GitHub Secret{bcolors.ENDC}\n")

def github_secret_kontrol():
    """GitHub Secret kontrolü yapar"""
    eksikler = []
    
    if not KABLO_TOKEN:
        eksikler.append("KABLO_TOKEN")
    
    if eksikler:
        print(f"\n{bcolors.FAIL}{'═'*60}")
        print(f"⚠️  EKSİK SECRET: {', '.join(eksikler)}")
        print('═'*60)
        print("GitHub Actions'da çalışıyorsanız, repository secret ekleyin:")
        print("  Settings → Secrets and variables → Actions → New repository secret")
        for eksik in eksikler:
            print(f"  Name: {eksik}")
            print(f"  Value: [değer]")
        print('═'*60 + f"{bcolors.ENDC}\n")
        return False
    return True

def m3u_kanal_isimleri_al(m3u_yolu):
    isimler = []
    if os.path.exists(m3u_yolu):
        with open(m3u_yolu, "r", encoding="utf-8") as dosya:
            for satir in dosya:
                if satir.startswith("#EXTINF"):
                    eslesme = re.search(r",(.+?)(?:\n|$)", satir)
                    if eslesme:
                        isimler.append(eslesme.group(1).strip())
    return isimler

def tarih_xmltv_formatina_cevir(tarih_str):
    try:
        tarih = datetime.strptime(tarih_str, "%d.%m.%Y %H:%M")
        return tarih.strftime("%Y%m%d%H%M%S +0300")
    except Exception as e:
        return ""

def epg_olustur(tum_kanallar, m3u_kanal_isimleri, epg_yolu):
    try:
        print(f"{bcolors.OKCYAN}[{zaman_damgasi()}] 📡 EPG oluşturuluyor...{bcolors.ENDC}")
        
        tv = ET.Element("tv", attrib={
            "source-info-name": "KablowebTV",
            "generator-info-name": "UmitEPGGenerator"
        })
        
        eklenen_kanal_sayisi = 0
        eklenen_program_sayisi = 0
        
        m3u_kanal_isimleri_lower = [isim.lower() for isim in m3u_kanal_isimleri]
        
        for kanal in tum_kanallar:
            isim = kanal.get("Name", "").strip()
            if not isim:
                continue
                
            kanal_lower = isim.lower()
            if kanal_lower not in m3u_kanal_isimleri_lower:
                found = False
                for m3u_isim in m3u_kanal_isimleri:
                    if isim.lower() in m3u_isim.lower() or m3u_isim.lower() in isim.lower():
                        found = True
                        break
                if not found:
                    continue
            
            kanal_id = str(kanal.get("UId", ""))
            if not kanal_id:
                kanal_id = re.sub(r'[^a-zA-Z0-9]', '_', isim)
            
            kanal_eleman = ET.SubElement(tv, "channel", id=kanal_id)
            
            display_name = ET.SubElement(kanal_eleman, "display-name")
            display_name.text = isim
            
            logo_url = kanal.get("PrimaryLogoImageUrl", "")
            if logo_url:
                ET.SubElement(kanal_eleman, "icon", src=logo_url)
            
            eklenen_kanal_sayisi += 1
            
            epgs = kanal.get("Epgs", [])
            for program in epgs:
                baslangic = program.get("StartDateTime", "")
                bitis = program.get("EndDateTime", "")
                baslik = program.get("Title", "")
                aciklama = program.get("ShortDescription", "")
                
                if not baslangic or not bitis or not baslik:
                    continue
                
                baslangic_xmltv = tarih_xmltv_formatina_cevir(baslangic)
                bitis_xmltv = tarih_xmltv_formatina_cevir(bitis)
                
                if not baslangic_xmltv or not bitis_xmltv:
                    continue
                
                program_eleman = ET.SubElement(tv, "programme", {
                    "start": baslangic_xmltv,
                    "stop": bitis_xmltv,
                    "channel": kanal_id
                })
                
                title = ET.SubElement(program_eleman, "title", lang="tr")
                title.text = baslik
                
                if aciklama:
                    desc = ET.SubElement(program_eleman, "desc", lang="tr")
                    desc.text = aciklama
                
                eklenen_program_sayisi += 1
        
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level + 1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        indent(tv)
        
        with open(epg_yolu, 'wb') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n'.encode('utf-8'))
            f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'.encode('utf-8'))
            tree = ET.ElementTree(tv)
            tree.write(f, encoding='utf-8')
        
        print(f"{bcolors.OKGREEN}[{zaman_damgasi()}] ✅ EPG oluşturuldu: {eklenen_kanal_sayisi} kanal, {eklenen_program_sayisi} program{bcolors.ENDC}")
        return True
    
    except Exception as hata:
        print(f"{bcolors.FAIL}[{zaman_damgasi()}] ❌ EPG oluşturma hatası: {str(hata)}{bcolors.ENDC}")
        return False

def kanallari_guncelle():
    try:
        baslik_yazdir()
        
        # Token kontrolü
        if not github_secret_kontrol():
            return False
        
        print(f"{bcolors.OKCYAN}[{zaman_damgasi()}] 🌐 API'den kanal verileri çekiliyor...{bcolors.ENDC}")
        
        response = requests.get(API_URL, headers=API_HEADERS, timeout=60)
        response.raise_for_status()
        
        try:
            veri = gzip.GzipFile(fileobj=BytesIO(response.content)).read().decode('utf-8')
        except:
            veri = response.content.decode('utf-8')
            
        json_veri = json.loads(veri)
        
        if not json_veri.get("IsSucceeded") or not json_veri.get("Data", {}).get("AllChannels"):
            print(f"{bcolors.FAIL}[{zaman_damgasi()}] ❌ Geçersiz kanal verisi alındı!{bcolors.ENDC}")
            return False

        tum_kanallar = json_veri["Data"]["AllChannels"]
        print(f"{bcolors.OKGREEN}[{zaman_damgasi()}] ✅ {len(tum_kanallar)} kanal bulundu{bcolors.ENDC}")

        # M3U dosyasını oluştur
        m3u_yolu = os.path.join(TEMEL_DIZIN, M3U_DOSYA_ADI)
        epg_yolu = os.path.join(TEMEL_DIZIN, EPG_DOSYA_ADI)
        
        print(f"{bcolors.OKCYAN}[{zaman_damgasi()}] 📝 M3U dosyası oluşturuluyor...{bcolors.ENDC}")
        
        with open(m3u_yolu, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            kanal_sayisi = 0
            kanal_index = 1
            
            for kanal in tum_kanallar:
                isim = kanal.get('Name')
                stream_data = kanal.get('StreamData', {})
                hls_url = stream_data.get('HlsStreamUrl') if stream_data else None
                logo = kanal.get('PrimaryLogoImageUrl', '')
                kategoriler = kanal.get('Categories', [])
                
                if not isim or not hls_url:
                    continue
                
                grup = kategoriler[0].get('Name', 'Genel') if kategoriler else 'Genel'
                
                # Bilgilendirme kategorisini atla
                if grup == "Bilgilendirme":
                    continue
                
                # GRUP_EKI varsa ekle
                if GRUP_EKI:
                    grup = f"{GRUP_EKI} {grup}"
                
                tvg_id = str(kanal_index)
                
                f.write(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{grup}",{isim}\n')
                f.write(f'{hls_url}\n')
                
                kanal_sayisi += 1
                kanal_index += 1
        
        print(f"{bcolors.OKGREEN}[{zaman_damgasi()}] ✅ M3U oluşturuldu! ({kanal_sayisi} kanal){bcolors.ENDC}")

        # EPG oluştur
        print(f"{bcolors.OKCYAN}[{zaman_damgasi()}] 📊 EPG oluşturuluyor...{bcolors.ENDC}")
        kanal_isimleri = m3u_kanal_isimleri_al(m3u_yolu)
        
        if kanal_isimleri:
            epg_olustur(tum_kanallar, kanal_isimleri, epg_yolu)
        else:
            print(f"{bcolors.WARNING}[{zaman_damgasi()}] ⚠️ EPG oluşturulamadı (kanal ismi bulunamadı){bcolors.ENDC}")

        # Sonuç raporu
        print(f"\n{bcolors.OKGREEN}{'═'*60}")
        print(f"{'✅ GÜNCELLEME TAMAMLANDI! ✅'.center(60)}")
        print(f"{'═'*60}{bcolors.ENDC}")
        
        print(f"{bcolors.BOLD}📊 İSTATİSTİKLER:{bcolors.ENDC}")
        print(f"   📺 Toplam Kanal: {kanal_sayisi}")
        
        # Dosya boyutlarını göster
        if os.path.exists(m3u_yolu):
            m3u_boyut = os.path.getsize(m3u_yolu) / 1024
            print(f"   📄 M3U Boyutu: {m3u_boyut:.2f} KB")
        
        if os.path.exists(epg_yolu):
            epg_boyut = os.path.getsize(epg_yolu) / 1024
            print(f"   📄 EPG Boyutu: {epg_boyut:.2f} KB")
        
        print(f"\n{bcolors.BOLD}📂 DOSYA KONUMLARI:{bcolors.ENDC}")
        print(f"   📄 M3U: {os.path.abspath(m3u_yolu)}")
        print(f"   📄 EPG: {os.path.abspath(epg_yolu)}")
        print(f"{'═'*60}\n")

        return True

    except Exception as hata:
        print(f"{bcolors.FAIL}[{zaman_damgasi()}] ❌ Kritik hata: {str(hata)}{bcolors.ENDC}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    kanallari_guncelle()
