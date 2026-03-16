import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import random
from groq import Groq  # Ollama yerine Groq kullanıyoruz

# --- WEB ARAYÜZ AYARLARI ---
st.set_page_config(page_title="Ticari İstihbarat Portalı", page_icon="🌐", layout="wide")

# --- YAPILANDIRMA ---
API_ANAHTARI = "ddee70325a54422194ebd75f895a14a5" 
BASE_URL = "https://newsapi.org/v2/everything"

GLOBAL_IZINLI_KAYNAKLAR = [
    "Reuters", "BBC News", "Bloomberg", "The Wall Street Journal", 
    "Financial Times", "Associated Press", "Al Jazeera English",
    "Anadolu Agency", "NTV", "Sözcü", "Hürriyet"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
}

# --- GROQ ANALİZ FONKSİYONU ---
def haberi_analiz_et(haber_metni):
    # Streamlit Secrets'tan API key alıyoruz
    try:
        groq_api_key = st.secrets["groq_key"]
        client = Groq(api_key=groq_api_key)
        
        prompt = f"""
        Aşağıdaki haber metnini bir ticari istihbarat analisti gibi incele ve sonucu TÜRKÇE olarak ver.
        Lütfen sadece Türkçe konuş.
        
        1. **Özet:** (Haberin can alıcı noktası nedir?)
        2. **Ticari/Ekonomik Etki:** (Hangi sektörleri nasıl etkiler? Fiyatlar, lojistik, arz-talep.)
        3. **Bireysel & Siyasi Varsayım:** (Bu olay siyasi dengeleri veya halkı nasıl etkiler?)
        4. **Risk Skoru:** (1-10 arası bir puan ver ve nedenini yaz.)
        
        Haber Metni:
        {haber_metni}
        """
        
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Analiz Hatası: {e}. (Lütfen Streamlit Secrets'ta groq_key tanımlandığından emin olun.)"

# --- HABER ARAMA VE İÇERİK ÇEKME FONKSİYONLARI ---
def haberleri_ara(kelime, dil='en', limit=1):
    params = {
        'q': kelime, 'sortBy': 'publishedAt', 'language': dil, 
        'pageSize': 50, 'apiKey': API_ANAHTARI 
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'ok' and data['totalResults'] > 0:
            filtrelenmis_sonuclar = []
            for article in data['articles']:
                kaynak_adi = article.get('source', {}).get('name')
                if any(izinli.lower() in kaynak_adi.lower() for izinli in GLOBAL_IZINLI_KAYNAKLAR):
                    filtrelenmis_sonuclar.append({
                        'Baslik': article.get('title'),
                        'Kaynak': kaynak_adi,
                        'URL': article.get('url'),
                        'Ozet': article.get('description')
                    })
                if len(filtrelenmis_sonuclar) >= limit: break
            return filtrelenmis_sonuclar
        return []
    except Exception as e:
        st.error(f"HATA [API]: {e}")
        return []

def icerik_kazı(haber_listesi):
    sonuclar = []
    for haber in haber_listesi:
        try:
            res = requests.get(haber['URL'], headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, 'lxml')
            paragraflar = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 100]
            tam_metin = "\n\n".join(paragraflar)
            haber['Makale_Metni'] = tam_metin if len(tam_metin) > 200 else f"Scraping sınırlı. Özet: {haber['Ozet']}"
            sonuclar.append(haber)
        except:
            haber['Makale_Metni'] = f"İçerik çekilemedi. Özet: {haber['Ozet']}"
            sonuclar.append(haber)
    return sonuclar

# --- STREAMLIT ARAYÜZÜ ---
st.title("📊 Ticari İstihbarat Analiz Sistemi")
st.markdown("Orijinal scraping algoritması ve Llama 3 (Groq) bulut altyapısı ile.")

# Yan Menü Ayarları
with st.sidebar:
    st.header("🔍 Arama Ayarları")
    anahtar_kelime = st.text_input("Takip edilecek konu:", "Global Semiconductor Market")
    haber_sayisi = st.slider("Haber Sayısı", 1, 5, 1)
    dil_secimi = st.selectbox("Haber Dili", ["en", "tr"])
    baslat_butonu = st.button("Analizi Başlat")

# Ana Akış
if baslat_butonu:
    with st.status("İşlem yürütülüyor...", expanded=True) as status:
        st.write("Adım 1: Haberler aranıyor...")
        bulunan_haberler = haberleri_ara(anahtar_kelime, dil=dil_secimi, limit=haber_sayisi)
        
        if bulunan_haberler:
            st.write(f"Adım 2: {len(bulunan_haberler)} adet güvenilir kaynak bulundu. İçerikler çekiliyor...")
            final_verileri = icerik_kazı(bulunan_haberler)
            
            status.update(label="Analiz Tamamlandı!", state="complete", expanded=False)
            
            for h in final_verileri:
                st.divider()
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("📰 Haber Bilgileri")
                    st.info(f"**Kaynak:** {h['Kaynak']}\n\n**Başlık:** {h['Baslik']}")
                    st.link_button("Orjinal Habere Git", h['URL'])
                
                with col2:
                    st.subheader("🧠 Llama 3 Stratejik Analiz")
                    with st.spinner("AI analiz raporu oluşturuyor..."):
                        analiz_sonucu = haberi_analiz_et(h['Makale_Metni'])
                        st.markdown(analiz_sonucu)
        else:
            status.update(label="Haber bulunamadı.", state="error")
            st.warning("Belirlediğiniz kriterlere ve güvenilir kaynak listesine uygun güncel haber bulunamadı.")
