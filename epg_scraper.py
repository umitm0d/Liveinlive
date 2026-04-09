#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from datetime import datetime, timedelta
import gzip

# ==========================================
# MANUEL SAAT AYARI (Kayma olursa buradan düzelt!)
# Örn: Saatler 3 saat ilerideyse -3 yap. Gerideyse 3 yap.
SAAT_AYARI = 3
# ==========================================

CHANNELS_DATA = {
    "TRT 1": "TRT1.tr", "Show TV": "ShowTV.tr", "Kanal D": "KanalD.tr", "ATV": "ATV.tr",
    "NOW": "NOWTV.tr", "Star TV": "StarTV.tr", "TV8": "TV8.tr", "360": "360TV.tr",
    "CNBC-e": "CNBC-e", "Bloomberg HT": "Bloomberg HT", "A Haber": "AHaber.tr", "TRT Haber": "TRTHaber.tr",
    "Kanal 7": "Kanal7.tr", "A2": "A2", "Beyaz TV": "BeyazTV.tr", "tv100": "TV100.tr",
    "Ülke TV": "Ülke TV", "TVNET": "TVNET", "Kanal 24": "Kanal 24", "24 TV": "24 TV",
    "NTV": "NTV.tr", "CNN Türk": "CNN Türk", "A Para": "A Para", "Habertürk": "Habertürk",
    "TGRT Haber": "TGRTHaber.tr", "Ekotürk": "Ekotürk", "Haber Global": "HaberGlobal.tr", "TELE1": "TELE1",
    "Ekol TV": "Ekol TV", "Flash Haber": "Flash Haber TV", "Lider Haber": "Lider Haber TV", "ULUSAL TV": "ULUSAL TV",
    "Halk TV": "HalkTV.tr", "Teve2": "Teve2.tr", "TV8.5": "TV85.tr", "TRT 3": "TRT 3 Spor",
    "TRT Avaz": "TRTAvaz.tr", "TRT Kurdi": "TRTKurdi.tr", "Türk Haber": "Türkhaber TV", "Sözcü TV": "Sözcü TV",
    "TRT Türk": "TRT Türk", "KRT": "KRT", "Bengütürk": "Bengütürk", "TV4": "TV 4",
    "TRT 2": "TRT2.tr", "VAV TV": "Vav TV", "Diyanet TV": "Diyanet TV", "Akit TV": "Akit TV",
    "GZT": "GZT", "Bi Kanal": "Bi Kanal", "MK TV": "MK TV", "TYT Türk": "TYT Türk",
    "TRT Spor": "TRT Spor", "A Spor": "A Spor", "HT Spor": "HT Spor", "FB TV": "FB TV",
    "Tivibu Spor": "Tivibu Spor", "Sıfır TV": "Sıfır TV", "TRT Spor Yıldız": "TRT Spor Yıldız", "TJK TV": "TJK TV",
    "Sports TV": "Sports TV", "TLC": "TLC", "TRT Müzik": "TRT Müzik", "TRT Arabi": "TRT Arabi",
    "A News": "A News", "BBC World": "BBC World", "TRT World": "TRT World", "TRT EBA": "TRT EBA",
    "TRT Çocuk": "TRT Çocuk", "STOON TV": "STOON TV", "Cartoon Network": "Cartoon Network", "Minika GO": "Minika GO",
    "Minika Çocuk": "Minika Çocuk", "DMAX": "DMAX", "Yaban TV": "Yaban TV", "TRT Belgesel": "TRT Belgesel",
    "TGRT Belgesel": "TGRT Belgesel"
}

# Kaynaktaki isim eşleştirmeleri
ALIAS_MAP = {
    "NOW": ["fox", "nowtv", "fox tv"], "TV8.5": ["tv85", "tv 8,5", "tv8bucuk", "tv 8.5"],
    "Sözcü TV": ["szctv", "sozcu"], "TRT Spor Yıldız": ["trtyildiz", "trtspor2"]
}

MASTER_URLS = ["https://www.open-epg.com/app/download.php?file=turkey3.xml"]

def fix_time(time_str, offset_hours):
    try:
        # Örnek: 20260315120000 +0000
        clean_time = time_str.split(' ')[0]
        dt = datetime.strptime(clean_time, "%Y%m%d%H%M%S")
        dt = dt + timedelta(hours=offset_hours)
        return dt.strftime("%Y%m%d%H%M%S") + " +0300"
    except:
        return time_str

def main():
    target_map = {name: {"epg_id": eid, "found": False} for name, eid in CHANNELS_DATA.items()}
    new_tv = ET.Element("tv", attrib={"generator-info-name": "BelesTiVi Fixed EPG"})

    for url in MASTER_URLS:
        try:
            resp = requests.get(url, timeout=40)
            root = ET.fromstring(resp.content)
            
            matched_channels = {}
            for channel in root.findall('channel'):
                m_id = channel.get('id')
                d_name = channel.find('display-name').text.lower().replace(" ", "")
                for name, data in target_map.items():
                    if not data["found"] and (name.lower().replace(" ", "") in d_name or any(a in d_name for a in ALIAS_MAP.get(name, []))):
                        data["found"] = True
                        ET.SubElement(new_tv, "channel", id=data["epg_id"]).append(ET.fromstring(f'<display-name>{name}</display-name>'))
                        matched_channels[m_id] = data["epg_id"]
            
            for prog in root.findall('programme'):
                m_cid = prog.get('channel')
                if m_cid in matched_channels:
                    prog.set('channel', matched_channels[m_cid])
                    # SAAT DÜZELTME BURADA YAPILIYOR
                    prog.set('start', fix_time(prog.get('start'), SAAT_AYARI))
                    prog.set('stop', fix_time(prog.get('stop'), SAAT_AYARI))
                    new_tv.append(prog)
        except: continue

    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(minidom.parseString(ET.tostring(new_tv, 'utf-8')).toprettyxml(indent="  "))

if __name__ == "__main__":
    main()
