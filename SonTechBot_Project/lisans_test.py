    import requests
import json

def check_license(license_key):
    """
    Verilen lisans anahtarını sunucuya göndererek geçerliliğini kontrol eder.
    
    Args:
        license_key (str): Kullanıcının girdiği lisans anahtarı.
        
    Returns:
        dict: Sunucudan gelen JSON yanıtını bir Python sözlüğü olarak döndürür.
              Eğer bir ağ hatası olursa, standart bir hata sözlüğü döndürür.
    """
    # !! KENDİ SİTE ADRESİNİZLE DEĞİŞTİRİN !!
    api_url = "https://www.41den.com/api/lisans_kontrol.php"
    
    # Sunucuya göndereceğimiz veri paketi
    payload = {
        'license_key': license_key
    }
    
    try:
        # POST isteğini gönderiyoruz. 5 saniye zaman aşımı eklemek iyi bir pratiktir.
        response = requests.post(api_url, data=payload, timeout=5)
        
        # Sunucudan başarılı bir yanıt (200 OK) geldiyse
        if response.status_code == 200:
            # Gelen JSON verisini Python sözlüğüne çevirip döndür
            return response.json()
        else:
            # Sunucu hatası (404 Not Found, 500 Internal Server Error vb.)
            return {
                'status': 'error',
                'message': f"Sunucu hatası: {response.status_code}",
                'data': None
            }
            
    except requests.exceptions.RequestException as e:
        # Ağ hatası (internet yok, siteye ulaşılamıyor vb.)
        return {
            'status': 'error',
            'message': f"Ağ hatası veya sunucuya ulaşılamıyor: {e}",
            'data': None
        }
    except json.JSONDecodeError:
        # Sunucudan gelen yanıt JSON formatında değilse
        return {
            'status': 'error',
            'message': "Sunucudan geçersiz bir yanıt alındı.",
            'data': None
        }

# --- FONKSİYONUN KULLANIM ÖRNEĞİ ---
if __name__ == "__main__":
    print("SonTechBot Lisans Aktivasyonu")
    
    # Kullanıcıdan lisans anahtarını al
    user_key_input = input("Lütfen lisans anahtarınızı girin: ").strip()
    
    if not user_key_input:
        print("Lisans anahtarı girmediniz.")
    else:
        print("\nLisans kontrol ediliyor, lütfen bekleyin...")
        
        # Fonksiyonu çağırarak lisansı kontrol et
        result = check_license(user_key_input)
        
        # Gelen yanıta göre işlem yap
        if result['status'] == 'success':
            print("\n-------------------------------------------")
            print("✓ BAŞARILI: Lisansınız doğrulandı!")
            print(f"Mesaj: {result['message']}")
            
            # Sunucudan gelen ek verileri alıp kullanabiliriz
            customer_data = result.get('data', {})
            if customer_data:
                print(f"Müşteri E-postası: {customer_data.get('customer_email')}")
                print(f"İzin Verilen Şube Sayısı: {customer_data.get('branches_allowed')}")
                print(f"Lisans Bitiş Tarihi: {customer_data.get('expires_at')}")
                #
                # --- BURADAN İTİBAREN PROGRAMINIZIN ANA PENCERESİNİ AÇABİLİRSİNİZ ---
                # ornegin: ana_programi_baslat(sube_limiti=customer_data.get('branches_allowed'))
                #
            print("-------------------------------------------")
            
        else: # result['status'] == 'error'
            print("\n-------------------------------------------")
            print("✗ HATA: Lisans doğrulanamadı.")
            # Sunucudan gelen spesifik hata mesajını göster
            print(f"Sebep: {result.get('message', 'Bilinmeyen bir hata oluştu.')}")
            print("-------------------------------------------")
            # Programı burada sonlandırabilir veya kullanıcıya tekrar deneme hakkı verebilirsiniz.

    # Programın kapanmaması için bekleme
    input("\nÇıkmak için Enter'a basın.")