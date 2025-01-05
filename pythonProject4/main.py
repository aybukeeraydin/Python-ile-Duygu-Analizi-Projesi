import pandas as pd
import re
from zemberek import TurkishMorphology

# Excel dosyasını okuma
file_path = "veri.xlsx"
data = pd.read_excel(file_path)

# "Cumle" ve "Sinif" sütunlarını al
metinler = data["Cumle"]
siniflar = data["Sinif"]

# Metinleri listeye çevir
metin_listesi = metinler.tolist()
sinif_listesi = siniflar.tolist()

metin_listesi_temiz = [re.sub(r'[\.,?;:\-]', '', str(metin).lower()) for metin in metin_listesi]
stopwords = [
    "ve", "ile", "de", "da", "için", "kadar", "ama", "fakat", "çünkü", "yani", "şimdi",
    "ise", "her", "bu", "şu", "o", "ne", "hangi", "buna", "şuna", "şey", "ki", "gibi"
]

# Stopwords'leri kaldırma
metin_listesi_temiz = [
    " ".join([kelime for kelime in metin.split() if kelime not in stopwords])
    for metin in metin_listesi_temiz
]
# Kelimelere ayırma
kelimelere_ayrilmis_metinler = [metin.split() for metin in metin_listesi_temiz]

# Zemberek Morphology Başlatma
morphology = TurkishMorphology.create_with_defaults()

# Negatif eklerin listesi
NEGATIF_EKLER = [
    "m:Neg", "ma:Neg", "me:Neg",  # Olumsuzluk ekleri
    "ama:Unable", "eme:Unable",  # Yetersizlik ekleri
    "maz:Neg", "mez:Neg",# -mez/-maz olumsuzluk eki
    "mama:Neg", "meme:Neg",  # -mama/-meme olumsuzluk eki
    "masa:CondNeg", "mese:CondNeg",  # Şart kipindeki olumsuzluk ekleri
    "mamış:PastPartNeg", "memiş:PastPartNeg",  # Geçmiş zaman olumsuzluk ekleri
    "mamalı:CondNecNeg", "memeli:CondNecNeg",  # Gereklilik kipindeki olumsuzluk ekleri
    "maş:PastCondNeg", "meş:PastCondNeg",  # Şartlı geçmiş olumsuz ekleri
    "mayacak:NegFut", "meyecek:NegFut",  # Gelecek zaman olumsuz ekleri
    "mazsa:CondNeg", "mezse:CondNeg",  # -mez/-maz ile Şart kipinin birleşimi
    "mamalıydı:CondNecPastNeg", "memeliydi:CondNecPastNeg",  # Geçmiş gereklilik olumsuz ekleri
    "sız:Without", "siz:Without",  # Yokluk ekleri (-sız, -siz)
    "suz:Without", "süz:Without",  # Bölgesel varyasyonlar (-suz, -süz)
    "madan:InfNeg", "meden:InfNeg",  # -madan/-meden zarf fiil eki
    "maksızın:InfNeg", "meksizin:InfNeg",  # -maksızın/-meksizin zarflar
]

# Olumsuz fiil köklerinin listesi
OLUMSUZ_FIILLER = [
    "öl", "kaybet", "sinirlen", "üz", "kork", "kaç", "yık", "çök", "ağla", "yak",
    "unut", "kır", "tüken", "soğut", "tiksin", "düş", "bat", "sil", "kız", "saldır",
    "öldür", "boz", "kapat", "kandır", "kopar", "zarar ver", "ihanet et", "ihmal et",
    "vur", "bağır"
]


# Pozitif ve Negatif kelimelerin olduğu Excel dosyasını okuma
keywords_file_path = "polarization_keywords.xlsx"
keywords_data = pd.read_excel(keywords_file_path)

# Tüm kelimeleri küçük harfe dönüştür
keywords_data["Kelime"] = keywords_data["Kelime"].str.lower()

# Pozitif ve Negatif kelimeleri listeye ayır
pozitif_kelimeler = keywords_data[keywords_data["Kategori"] == "Pozitif"]["Kelime"].tolist()
negatif_kelimeler = keywords_data[keywords_data["Kategori"] == "Negatif"]["Kelime"].tolist()

NEGATIF_KELIMELER = negatif_kelimeler
POZITIF_KELIMELER = pozitif_kelimeler

def negatif_kontrol(metin):
    deg_kok = kelime_koku_bul("değil")[0]  # "değil" kelimesinin kökü
    yok_kok = kelime_koku_bul("yok")[0]  # "yok" kelimesinin kökü

    # Cümlede "değil" ve "yok" kelimelerinin bulunup bulunmadığını kontrol et
    degil_var = any(deg_kok in kelime_koku_bul(kelime)[0] for kelime in metin)
    yok_var = any(yok_kok in kelime_koku_bul(kelime)[0] for kelime in metin)

    # Eğer "yok" ve "değil" birlikte varsa, pozitif kabul et
    if yok_var and degil_var:
        return False # Pozitif kabul edilir

    # Eğer sadece "değil" veya "yok" varsa, negatif kelimelerle kontrol yap
    if degil_var or yok_var:
        for negatif_kelime in NEGATIF_KELIMELER:
            if negatif_kelime in metin:
                return False  # Negatif kelime varsa "pozitif" say (False döner)
        return True  # Sadece "değil" veya "yok" varsa "negatif" kabul edilir (True döner)

    return False  # Eğer "değil" ve "yok" yoksa herhangi bir işlem yapılmaz

def kelime_turu_belirle(kelime):
    analysis = morphology.analyze(kelime)
    results = [str(result) for result in analysis]

    # Fiilimsi kontrolü (sıfat fiil veya zarf fiil)
    if any("Inf2→Noun+A3sg" in result for result in results):  # Fiilimsilerde "VerbPart" bulunur
        return ["Fiilimsi"]  # Fiilimsi olarak döndür

    return results if results else ["Belirlenemedi"]


def kelime_koku_bul(kelime):
    analysis = morphology.analyze(kelime)
    stems = [result.get_stem() for result in analysis if result.get_stem()]
    return stems if stems else ["Kök Bulunamadı"]

def kelime_eklerini_bul(kelime):
    analysis = morphology.analyze(kelime)
    ek_listesi = []
    for result in analysis:
        analysis_detail = result.format_string()
        if '+' in analysis_detail:
            ekler = analysis_detail.split('+')[1:]  # İlk kısım kök, '+' sonrası ekler
            ek_listesi += ekler
    return ek_listesi if ek_listesi else ["Ek Bulunamadı"]

def polarizasyon_hesapla(metin_bilgisi, orijinal_metin):
    polarizasyon = 0
    etkileyenler = []
    for kelime, bilgiler in metin_bilgisi.items():
        # Eğer kelime fiilimsi ise, olumsuz ekleri kontrol etme
        if "Fiilimsi" in bilgiler["tur"]:
            etkileyenler.append(f"Fiilimsi yüzünden es geçildi: Kelime --> {kelime}")
            continue  # Fiilimsi ise olumsuz ekleri atla

        # Negatif ekleri kontrol et
        negatif_ek_sayisi = sum(1 for ek in bilgiler["ekler"] if any(negatif_ek in ek for negatif_ek in NEGATIF_EKLER))
        if negatif_ek_sayisi > 0:
            etkileyenler.append(f"Negatif ek: {kelime} ({negatif_ek_sayisi})")
        polarizasyon -= negatif_ek_sayisi

        kelime_kok = bilgiler["kök"][0]
        # Negatif kelimeleri kontrol et
        if kelime in NEGATIF_KELIMELER:
            etkileyenler.append(f"Negatif kelime: {kelime}")
            polarizasyon -= 1  # Her negatif kelime için polarizasyonu azalt
        if kelime in POZITIF_KELIMELER:
            etkileyenler.append(f"Pozitif kelime: {kelime}")
            polarizasyon += 1
        # Olumsuz fiil köklerini kontrol et
          # Kelimenin kökünü al
        if kelime_kok in OLUMSUZ_FIILLER:
            etkileyenler.append(f"Olumsuz fiil: {kelime_kok}")
            polarizasyon -= 1  # Eğer kök olumsuz fiil listesinde varsa polarizasyonu azalt

    # Hoş bir kelime ve "değil" varsa negatif kabul et
    if negatif_kontrol(orijinal_metin):
        etkileyenler.append(f"Olumsuz yapı: 'değil' veya 'yok' tespit edildi")
        polarizasyon = -1  # Hoş bir kelime ve "değil" varsa polarizasyon negatif

    return polarizasyon, etkileyenler

# Veriyi işleyip sonuçları saklama
sonuclar = []
sayaclar = {"DP": 0, "YP": 0, "YN": 0, "DN": 0}  # DP, YP, YN, DN sayacları

for i, metin in enumerate(kelimelere_ayrilmis_metinler):
    metin_bilgisi = {
        kelime: {
            "tur": kelime_turu_belirle(kelime),
            "kök": kelime_koku_bul(kelime),
            "ekler": kelime_eklerini_bul(kelime),
        }
        for kelime in metin
    }

    # Polarizasyon hesaplama
    polarizasyon, etkileyenler = polarizasyon_hesapla(metin_bilgisi, metin)

    # Polarizasyon değerini "pozitif" veya "negatif" olarak sınıflandırma
    polarizasyon_sinif = "negatif" if polarizasyon < 0 else "pozitif"

    if isinstance(sinif_listesi[i], str):
        sinif = sinif_listesi[i].lower()  # String ise küçük harfe çevir
    else:
        continue  # Float ise bu elemanı atla

    # Karşılaştırma: Sinif ve Polarizasyonu karşılaştır
    sinif_lower = sinif
    polarizasyon_lower = polarizasyon_sinif.lower()

    if sinif_lower == "pozitif" and polarizasyon_lower == "pozitif":
        sonuc = "DP"
        sayaclar["DP"] += 1
    elif sinif_lower == "pozitif" and polarizasyon_lower == "negatif":
        sonuc = "YP"
        sayaclar["YP"] += 1
    elif sinif_lower == "negatif" and polarizasyon_lower == "pozitif":
        sonuc = "YN"
        sayaclar["YN"] += 1
    elif sinif_lower == "negatif" and polarizasyon_lower == "negatif":
        sonuc = "DN"
        sayaclar["DN"] += 1

    # Sonuçları sakla
    sonuclar.append([metin_listesi[i], sinif, polarizasyon_sinif, polarizasyon, sonuc, ", ".join(etkileyenler)])

# DataFrame oluşturma ve Excel dosyasına kaydetme
output_df = pd.DataFrame(
    sonuclar,
    columns=["Cümle", "Sinif", "Polarizasyon", "Polarizasyon Skoru", "Sonuç", "Etkileyen Unsurlar"]
)

# DP, YP, YN, DN sayılarının olduğu yeni DataFrame oluşturma
sayaclar_df = pd.DataFrame(list(sayaclar.items()), columns=["Sonuç Türü", "Sayısı"])

# Excel dosyasına iki sayfa ekleme
with pd.ExcelWriter("output.xlsx") as writer:
    output_df.to_excel(writer, index=False, sheet_name="Cümle Verisi")
    sayaclar_df.to_excel(writer, index=False, sheet_name="Sonuç Sayıları")

print("Sonuçlar 'output.xlsx' dosyasına kaydedildi.")
print(sayaclar)

# Performans değerleri hesaplama
def performans_degerleri(sayaclar):
    dp = sayaclar.get("DP", 0)
    yp = sayaclar.get("YP", 0)
    yn = sayaclar.get("YN", 0)
    dn = sayaclar.get("DN", 0)

    tum_tahminler = dp + yp + yn + dn
    doğruluk = (dp + dn) / tum_tahminler if tum_tahminler != 0 else 0
    kesinlik = dp / (dp + yp) if (dp + yp) != 0 else 0
    anma = dp / (dp + yn) if (dp + yn) != 0 else 0
    f1 = (2 * kesinlik * anma) / (kesinlik + anma) if (kesinlik + anma) != 0 else 0

    return {
        "Doğruluk": doğruluk,
        "Kesinlik": kesinlik,
        "Anma": anma,
        "F1 Ölçütü": f1
    }

performans = performans_degerleri(sayaclar)
print("Doğruluk:", performans["Doğruluk"])
print("Kesinlik:", performans["Kesinlik"])
print("Anma:", performans["Anma"])
print("F1 Ölçütü:", performans["F1 Ölçütü"])