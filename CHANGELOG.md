# Değişiklik Günlüğü

## 1.3.0

### Kedi görselleri ve animasyon
- Tüm kedi görselleri tek bir referanstan, aynı stilde yeniden üretildi (Google Flow). Pozlar aynı ölçekte ve aynı zemin çizgisinde.
- Görseller kareye gerilmiyor; en-boy oranı korunup alta oturtuluyor.
- İlk yürüme karesi (`cat_walk.PNG`) artık oynatılıyor; yürüme 6 kare.
- Yürüme karesi alınan yola göre ilerliyor, ayaklar kaymıyor.
- `tools/build_sprites.py`: Flow sprite sayfalarından görselleri üreten araç.

### Düzeltmeler
- EXE'de görsel değiştirme çalışmıyordu. Seçilen görsel artık kalıcı veri klasörüne kopyalanıyor ve hemen yükleniyor.
- Görsellerdeki siyah pikseller şeffaf görünüyordu. Şeffaflık anahtarı nadir bir renge alındı, yarı saydam kenarlar ayıklanıyor.
- Ev menüsündeki Gizle butonunun ve `show_names_info` metninin çevirisi eksikti. İki dilde de tüm anahtarlar tamamlandı.
- Tepsi menüsü dil değişince güncelleniyor.
- Pencere DPI farkında. %125 ve %150 gibi ölçeklerde ekranın tamamını kaplıyor.
- Kedi tüm monitörlerde dolaşabiliyor. Her monitörün DPI ölçeğine göre boyutlanıyor.
- Eve çift tıklama hiç çalışmıyordu (sürükleme önce yakalanıyordu).
- Windows ile başlatma açıkken EXE taşınırsa kayıt yeni yere güncelleniyor.

### Tamamlanan özellikler
- Uyku istatistiği çalışıyor: uyanıkken azalıyor, uyurken doluyor. Yorgun kedi eve gidip uyuyor.
- Yaş gün olarak artıyor.
- Kedi, ev ve top için renk seçenekleri gerçekten görseli değiştiriyor.
- Mutluluk, açlık, uyku, kedi ve ev konumu kaydediliyor.
- İstatistikler saatler içinde düşüyor (önce 17-33 dakikaydı).
- Topu yakalamak mutluluk veriyor. Top fırlatılabiliyor.
- Gizlenince bildirim çıkıyor. Ev menüsünde ve ayarlarda Çıkış butonu var.
- Uygulamanın kendi ikonu var (EXE, tepsi, pencere).

### Proje
- Kod `screenpet` paketinde modüllere bölündü.
- README, LICENSE, requirements.txt, .gitignore, CHANGELOG ve birim testleri eklendi.
- Sürüm numarası `screenpet/__init__.py` içinde. EXE'nin dosya özelliklerinde de görünüyor.

## 1.2
- Sistem tepsisi, Windows ile başlatma, PyInstaller paketi.
