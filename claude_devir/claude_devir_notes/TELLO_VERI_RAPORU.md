# TelloPy ile Tello'dan okunan veriler

Bu belge, TelloPy'nin (`TelloPy/` klasöründeki 0.8.0.dev0 sürümü) drone'dan **doğrudan** aldığı verileri listeler.
Bu verilerden hesaplanan değerler (açı dönüşümü vb.) burada veri olarak yer almıyor.
Tek istisna, kütüphanenin zaman düzeltmesi: §2'de nasıl çalıştığı anlatılıyor.

Kaynaklar:
- **Kod:** `tellopy/_internal/protocol.py`, `tello.py`, `video_stream.py`, `estimator.py`; tip ve byte konumları buradan alındı.
- **Belge:** `TelloPy/docs/sensor_time.md`; Eylül 2026'da tek bir drone ile yapılmış ölçümler.
- **Kayıtlar:** `TelloPy/tests/data/*.jsonl`, iki uçuş (65 s ve 95 s).
- **Bizim test uçuşumuz (11 Kasım 2026):** `kayitlar/paket_dinleme_20261111_105319/`, `tello_paket_dinle.py --ucus --hareket` ile. Toplam 79 s: 30 s yerde, kalkış, 15 s havada bekleme, sağa/sola dönüş, ileri/geri itiş, iniş. Drone'dan gelen 2364 paketin hepsi ham olarak kaydedildi.
- **İkinci test uçuşu (11 Kasım 2026):** `kayitlar/paket_dinleme_20261111_143727/`, `tello_paket_dinle.py --ucus --eksen --elle 60` ile. Her eksen ayrı ayrı oynatıldı, inişten sonra drone elle eğildi, çevrildi, kaldırıldı ve alt kamerası kapatıldı. Günlük kayıtlarının çoğu bununla çözüldü (§4.6).

İşaretler: **✈** = bizim test uçuşumuzda ölçüldü, **✔** = TelloPy'nin ölçümü / koddan kesin, **~** = topluluk bilgisi, doğrulanmamış, **?** = bilinmiyor.

> **TelloPy düzeltildi (§9).** Bu rapor düzeltilmiş kütüphaneyi anlatır.
> - **Kurulum:** Kütüphane, `pip install -e TelloPy` ile kaynaktan (düzenlenebilir) kurulu. `TelloPy/` klasöründeki her değişiklik hemen geçerli olur.
> - **Testler:** Kütüphanenin 144 çevrimdışı testi geçiyor (`python -m unittest discover -s tests -t . -p "test_*.py"`, `TelloPy/` içinde).
> - **Değişiklikleri görmek için:** `git diff`, `TelloPy/` içinde.

İçindekiler:
1. Özet tablosu
2. Zaman damgaları ve kütüphanenin zaman düzeltmesi
3. Uçuş durumu (FlightData)
4. Uçuş günlüğü kayıtları (IMU, MVO, gyro, ToF, kontrol)
5. Diğer drone mesajları
6. Görüntü
7. Komut yanıtları
8. Güvenilirlik notları
9. Kütüphanede bulunan ve düzeltilen hatalar
10. Tüm verileri okuma örneği

---

## 1. Özet: hangi veri nereden, ne sıklıkta, zaman damgası var mı?

| Veri | Olay (subscribe) | Gönderen | Sıklık | Drone zaman damgası (`tick`) | Bilgisayar zamanı (`recv_time`) | Güvenilirlik özeti |
|---|---|---|---|---|---|---|
| Uçuş durumu (`FlightData`) | `EVENT_FLIGHT_DATA` | drone, kendiliğinden | **10.0 Hz** ✈ | **yok** | var | Sayılar artık doğru okunuyor (§9.1). Bazı alan adları yanıltıcı (§3) |
| IMU (`LogImuAtti`) | `EVENT_SAMPLE_IMU` | drone uçuş günlüğü | **10 Hz** ✈ (79 s'de 774 kayıt, ~%2 eksik); TelloPy'nin uçuşlarında 8.0–8.8 Hz ✔ | **var** | var | Bağlantı başında 3 eski kayıt ✈ |
| Gyro (`LogGyro`) | `EVENT_SAMPLE_GYRO` | drone uçuş günlüğü | **20 Hz, sadece havada** ✈; TelloPy'nin uçuşlarında 16.6–17.2 Hz ✔ | **var** | var | Yerde hiç gelmiyor ✈ |
| Optik akış odometrisi (`LogNewMvoFeedback`, MVO) | `EVENT_SAMPLE_MVO` | drone uçuş günlüğü | **5 Hz** ✈ | **var** | var | IMU'ya göre 0.2–0.9 s gecikmeli ✔. Kalkışta konumu büyük bir sıçrama yapıyor ✈ (§4.2) |
| ToF mesafe (`LogTof`) | `EVENT_SAMPLE_TOF` | drone uçuş günlüğü | **5 Hz** ✈ | **var** | var | Birimi **mm** ✈; yerde 100 (en küçük değer) |
| Kontrol büyüklükleri (`LogControl`) | `EVENT_SAMPLE_CONTROL` | drone uçuş günlüğü | **20 Hz, sadece havada** ✈ | **var** | var | Roll/pitch/yaw/itki çıkışları (§4.5) |
| Sonradan çözülen 8 kayıt (§4.6): çubuklar, motorlar, konum, barometre, pil gerilimi… | `EVENT_SAMPLE_RAW` | drone uçuş günlüğü | 1.7–10 Hz ✈ | **var** | var | Alanlar iki gerçek uçuşla doğrulandı ✈ |
| Çözülmeyen günlük kayıtları (§4.7) | `EVENT_SAMPLE_RAW` | drone uçuş günlüğü | 9 tür, 0.5–5 Hz ✈ | **var** | var | Sadece ham byte (`payload`) |
| Wi-Fi | `EVENT_WIFI` | drone | **1 Hz** ✈ | yok | var | Güç ve parazit `FlightData`'ya da yazılıyor (§9.3) |
| Işık | `EVENT_LIGHT` | drone | **0.5 Hz** ✈ | yok | var | `FlightData.light_strength`'e yazılıyor (§9.3) |
| Görüntü (H.264) | `get_video_stream()` / `EVENT_VIDEO_FRAME` | drone, UDP 6038 | **32 kare/s** ✈ | **yok** | UDP paketi başına var | Bağlantı kopup gelince akış yeniden açılıyor (§9.5) |
| Komut yanıtı (ACK) | `EVENT_SAMPLE_COMMAND_ACK` / `_TIMEOUT` | drone | gönderdiğimiz komut başına | yok | var | Gidiş-dönüş medyan 44 ms, %2 yanıtsız ✔ |
| IMU kalibrasyon durumu | `EVENT_CALIBRATION_STATUS` | drone | sadece kalibrasyon sırasında | yok | var | — |
| Fotoğraf dosyası | `EVENT_FILE_RECEIVED` | drone | `take_picture()` sonrası | yok | var | JPEG byte'ları |
| Günlük başlığı | `EVENT_LOG_HEADER` | drone | bağlanınca bir kez | yok | var | Firmware derleme metni içerir |
| Zaman isteği | `EVENT_TIME` | drone | **0.4 Hz** (2.5 s'de bir) ✈ | yok | var | Drone saati soruyor, içerik boş ✈; TelloPy artık yanıtlıyor (§9.15) |
| Günlük ayarı | `EVENT_LOG_CONFIG` | drone | **0.5 Hz** ✈ | yok | var | Hep aynı 58 byte ✈; çözülmüyor |
| Bağlantı kuruldu/koptu | `EVENT_CONNECTED` / `EVENT_DISCONNECTED` | **bilgisayar** (TelloPy) | durum değişince | yok | — | Kopma = 2 s hiç paket gelmemesi |

---

## 2. Zaman damgaları ve kütüphanenin zaman düzeltmesi

### 2.1 Ham verideki zaman alanları

| Alan | Kimin saati | Tip | Açıklama |
|---|---|---|---|
| `recv_time` | Bilgisayar, `time.monotonic()` | float, saniye | UDP paketinin bilgisayara **ulaştığı** an. Ölçüm anı değil, her zaman ondan sonra. Bir günlük paketindeki tüm kayıtlar aynı `recv_time`'ı taşır. |
| `tick` | Drone donanım sayacı | uint32 | ~2 344 062 Hz ✔ (iki uçuşta 2 343 890 ve 2 343 970 Hz). ~30.5 dakikada başa döner. Ölçümün drone'daki zamanı bu. Sadece uçuş günlüğü kayıtlarında var. |
| `event_time` | — | float | Ham veride her zaman `recv_time` ile **aynı**. Zaman düzeltmesi kurulursa düzeltilmiş kopyada doldurulur (§2.2). |
| `event_time_std` | — | float veya None | Ham veride `None`. Düzeltilmiş kopyada `event_time`'ın belirsizliği (saniye). |
| `count` | TelloPy | int | Kaçıncı günlük paketi olduğu. Aynı paketteki kayıtlarda aynı. |

`recv_time` neden yetmiyor: Paketler Wi-Fi'da değişken sürede geliyor ve bir pakette daha önce ölçülmüş kayıtlar da var. Bu yüzden `recv_time` ölçüm anından hem geç hem titrek. Varış zamanları gerçek doğrudan 23–27 ms (std) sapıyor ✔.

### 2.2 Kütüphane zamanı nasıl düzeltiyor? (TickClock + Retimer)

**Kendiliğinden çalışmaz.** TelloPy ham verilere dokunmaz. Düzeltme ayrı bir katman (`estimator.py`); sizin kurmanız gerekir (örnek §10'da).

```
EVENT_SAMPLE_IMU ──> ImuContainer ──> TickClock ──(ClockSample)──┐
                                                                  ├──> Retimer ──> event_time düzeltilmiş kopya
EVENT_SAMPLE_IMU/GYRO/MVO ──> Container ─────────────────────────┘
```

**1. Container:** İlgili olaya abone olur ve son 10 saniyenin kayıtlarını tutar. Hazır olanlar: `ImuContainer`, `GyroContainer`, `StickContainer`. MVO, ToF ve kontrol için hazır Container yok; §10'daki gibi iki satırla tanımlanabilir.

**2. TickClock** (`estimator.py`). Drone sayacından bilgisayar saatine geçiş doğrusunu bulur: `bilgisayar_saati = a + tick / frekans`.
- **Girdi:** Sadece IMU kayıtları. Gyro eklenince tahmin 13–16 ms kaydığı için kütüphane yalnız IMU'yu seçmiş ✔.
- **Paket başına bir nokta:** Aynı `recv_time`'ı taşıyan kayıtlar tek paket sayılır. Sadece **en büyük tick'li** (en taze) kayıt kullanılır, çünkü eski kayıtlar pakette beklemiş olur. Bunu anlamak için her paket, bir sonraki gelene kadar bekletilir.
- **Başa dönme:** 32 bit sayaç taşınca en yakın fark alınarak kesintisiz sayıya çevrilir.
- **Başlangıç (eski kayıtları elemek):**
  - Her aday için, sayaç nominal hızda (2 344 062 Hz) çalışsaydı "sayacın sıfır olduğu an" hesaplanır.
  - Bu anlar medyandan 0.5 s içindeyse aday kabul edilir. Bağlantı başındaki eski kayıtlar burada elenir (§8.2).
  - 5 uyumlu paket birikince **kaba tahmin** başlar (frekans nominal kabul edilir, ±3·10⁻⁴).
  - 30 uyumlu pakette **asıl tahmin** başlar; frekans da ölçülür.
- **Doğru uydurma:** Son 60 s'lik paketlere en küçük kareler. Toplamlar eklenip çıkarılarak güncellendiği için paket başı maliyet sabit.
- **Aykırı paketler:** Doğrudan 5σ'dan (en az 5 ms) uzak paket kullanılmaz. Arka arkaya 20 paket dışlanırsa saat baştan başlar.
- **Çıktı (her pakette bir `ClockSample`):**
  - `host_at_tick`, `freq`: doğru.
  - `host_at_tick_std`, `freq_std`: doğrunun güvenilirliği.
  - `residual_std`: varışların doğrudan saçılması.
  - `n`: kaç paketle hesaplandığı; 0 ise tahmin yok.
  - `rejected`, `resets`: dışlanan paket ve baştan başlama sayıları.

**3. Retimer.** Her kaydın **kopyasını**, `event_time`'ı tick'ten hesaplanmış olarak yeniden yayınlar:
- `event_time = host_at_tick + (tick − saatin_tick'i) / freq`
- `event_time_std = hypot(host_at_tick_std, uzaklık × freq_std / freq)`
- **Düzeltilemezse:** Saat henüz hazır değilse, sonuç `recv_time`'dan 0.5 s'den fazla uzaksa ya da kayıtta tick yoksa kayıt olduğu gibi geçer. Bu durumda `event_time_std = None` olur; düzeltilip düzeltilmediğini bu alandan anlarsınız.
- Orijinal kayıt değiştirilmez.

**Neyi düzeltir, neyi düzeltemez:**
- ✔ **Titreşim:** Paket gecikmesinin oynayan kısmını giderir. Ölçülen aralıkların saçılması gyro'da 0.8–1.3 ms'den 0.1–0.2 ms'ye, IMU'da 1.0–1.4 ms'den 0.4 ms'ye iniyor ✔. Saatin belirsizliği uçuş başında ≥10 ms, sonunda 2.0–2.4 ms ✔.
- ✘ **Sabit gecikme:** Paketin en az yolculuk süresi düzeltilmiş zamanda kalır. Telemetriden bilinemez, komut gidiş-dönüşünden de çıkarılamaz (çok gürültülü).
- ✘ **Tick'i olmayan veriler:** FlightData, görüntü, Wi-Fi ve ışık düzeltilemez; onlarda sadece `recv_time` var.

---

## 3. Uçuş durumu: `FlightData` (`EVENT_FLIGHT_DATA`)

Paket kodu `0x0056`. Drone kendiliğinden gönderir, ~10 Hz. Her pakette yeni bir nesne gelir.
Zaman: sadece `recv_time`. int16 alanları artık doğru okunuyor (§9.1).

Test uçuşunda ✈ şu bitler hep 0 kaldı: `drone_hover`, `down_visual_state`, `imu_state`, `pressure_state`, `battery_state`, `power_state`, `gravity_state`, `wind_state`, `battery_low`, `front_*`, `factory_mode`, `outage_recording`, `camera_state`, `electrical_machinery_state`, `imu_calibration_state`, `throw_fly_timer`. Ya o durumlar oluşmadı ya da bitlerin anlamı farklı; bunlara güvenmeyin. `temperature_height` inişten sonra bir an 1 oldu.

| Alan | Byte | Ham tip | Birim | Not |
|---|---|---|---|---|
| `height` | 0–1 | int16 | **dm** ✈ | Havada 13 dm iken ToF 1.265 m ✈ |
| `north_speed` | 2–3 | int16 | dm/s ~ | **Dünya x ekseninde hız** (yaw 0° yönü) ✈. İlk iki uçuşta drone yaw ≈ −12° dönük olduğundan "ileri hız" sanılmıştı; yaw 80° iken yapılan üçüncü uçuşta ileri itiş `east_speed`'de göründü (§4.6) |
| `east_speed` | 4–5 | int16 | dm/s ~ | **Dünya y ekseninde hız** (yaw +90° yönü) ✈. Gövdeye göre değil |
| `ground_speed` | 6–7 | int16 | dm/s ~ | Adı yanıltıcı: **dikey hız, aşağı +** ✈ (kalkışta −9…−1, inişte +5…+1) |
| `fly_time` | 8–9 | int16 | **0.1 s** ✈ | Saniyede 10 artıyor, sadece havada; 256'yı geçince doğru (326, 359) ✈ |
| `imu_state` | 10, bit 0 | 0/1 | — | |
| `pressure_state` | 10, bit 1 | 0/1 | — | |
| `down_visual_state` | 10, bit 2 | 0/1 | — | Alt kamera (optik akış) durumu ~ |
| `power_state` | 10, bit 3 | 0/1 | — | |
| `battery_state` | 10, bit 4 | 0/1 | — | |
| `gravity_state` | 10, bit 5 | 0/1 | — | |
| `wind_state` | 10, bit 7 | 0/1 | — | |
| `imu_calibration_state` | 11 | uint8 | — | |
| `battery_percentage` | 12 | uint8 | % | |
| `drone_battery_left` | 13–14 | int16 | ? | **Hep 0** ✈ |
| `drone_fly_time_left` | 15–16 | int16 | **mV** ✈ | Adı yanlış: **pil gerilimi** ✈ (yerde 4218, uçuşta 3830'a düşüyor, inince 4115'e çıkıyor). TelloPy bu iki alanın adını ters koymuş: TelloLib ve SMerrony/tello aynı byte'ları pil gerilimi (mV) olarak okuyor |
| `em_sky` | 17, bit 0 | 0/1 | — | 1 = havada ✈ (kalkıştan ~0.5 s sonra 1, inişte 0) |
| `em_ground` | 17, bit 1 | 0/1 | — | **"Yerde" demek değil** ✈: sadece kalkışta motorlar dönmeye başlarken ~0.5 s 1 oluyor. Yerde olmayı `em_sky = 0` ve `em_open = 0` gösterir |
| `em_open` | 17, bit 2 | 0/1 | — | 1 = motorlar dönüyor ✈ |
| `drone_hover` | 17, bit 3 | 0/1 | — | |
| `outage_recording` | 17, bit 4 | 0/1 | — | |
| `battery_low` | 17, bit 5 | 0/1 | — | Düşük pil uyarısı |
| `battery_lower` | 17, bit 6 | 0/1 | — | Kritik pil ~ |
| `factory_mode` | 17, bit 7 | 0/1 | — | |
| `fly_mode` | 18 | uint8 | — | ✈ 6 = yerde / havada sabit, 11 = kalkış, 12 = iniş |
| `throw_fly_timer` | 19 | uint8 | ? | |
| `camera_state` | 20 | uint8 | — | |
| `electrical_machinery_state` | 21 | uint8 | — | Motor durumu ~ |
| `front_in` / `front_out` / `front_lsc` | 22, bit 0/1/2 | 0/1 | — | |
| `temperature_height` | 23, bit 0 | 0/1 | — | Sıcaklık uyarısı ~ |
| `wifi_strength` | — | uint8 | ? | **Bu paketten gelmez**; son `EVENT_WIFI` mesajının 1. byte'ı kopyalanır |
| `wifi_disturb` | — | uint8 | ? | Son `EVENT_WIFI` mesajının 2. byte'ı (parazit ~) |
| `light_strength` | — | uint8 | ? | Son `EVENT_LIGHT` mesajının 1. byte'ı (ışık seviyesi ~) |
| `smart_video_exit_mode` | — | — | — | Hiç doldurulmaz, hep 0 (bu bilgiyi taşıyan mesaj işlenmiyor) |

---

## 4. Uçuş günlüğü kayıtları

Paket kodu `0x1051`. Bir paket birden çok **kayıt** taşır. Her kaydın kendi `tick`'i vardır.

Okuma yolları:
- **`EVENT_SAMPLE_IMU`, `_MVO`, `_GYRO`, `_TOF`, `_CONTROL`, `_RAW` (önerilen):** Her kayıt için ayrı ayrı çağrılır. `data` o kaydın kendisidir; yeni bir nesnedir ve sonradan değişmez.
- **`EVENT_LOG_DATA`:** Paket başına bir kez çağrılır ve `data` her seferinde **aynı nesnedir** (§8.6).
  - `data.records`: Bu paketteki kayıtlar.
  - `data.mvo` / `data.imu`: O ana kadarki **son** MVO ve IMU kaydı; bu pakette olmayabilir.

Kayıt çerçevesi (TelloPy çözer): `0x55` | uzunluk (int16) | checksum (1 byte, kontrol edilmez) | kayıt id (uint16) | tick (uint32) | payload (tick'in ilk byte'ı ile XOR'lanmış) | CRC (2 byte, kontrol edilmez).
Her kayıtta ortak alanlar: `tick`, `recv_time`, `count`, `record_id`, `payload` (ham byte'lar, her zaman saklanır).

### 4.1 IMU: `LogImuAtti` (id 2048) — 10 Hz ✈

| Alan | Payload byte | Tip | Birim | Not |
|---|---|---|---|---|
| `acc_x`, `acc_y`, `acc_z` | 20, 24, 28 | float32 | ? (g olabilir ~) | Gövde ivmesi |
| `gyro_x`, `gyro_y`, `gyro_z` | 32, 36, 40 | float32 | ? (rad/s olabilir ~) | Açısal hız |
| `q0`, `q1`, `q2`, `q3` | 48, 52, 56, 60 | float32 | birimsiz | Yönelim kuaterniyonu, q0 = w. Bundan çıkan roll/pitch çubuk komutlarını temiz takip ediyor ✔ |
| `lin_acc_x/y/z` | 64, 68, 72 | float32 | m/s² | Dünya eksenine çevrilmiş, yerçekimi çıkarılmış ivme (0.95–0.98 korelasyon ✔) |
| `vg_x/y/z` | 76, 80, 84 | float32 | **m/s** ✈ | **Hız, dünya ekseninde**: x yaw 0° yönü, y yaw +90° yönü, z aşağı ✈. Yaw ile döndürünce gövde hızı çıkıyor: üçüncü uçuşta (yaw 80°) ileri itiş ileri +0.37, yana kaçak 0.01 m/s |
| `baro_raw` | 16 | float32 | m | **Barometre irtifası**, ham ✈. Sadece farkı anlamlı (odada 58–60 gösteriyor) |
| `baro` | 44 | float32 | m | Barometre irtifası, yumuşatılmış ✈. 1.2 m yükselince ~1.0 artıyor; ToF ile r = 0.99 |
| `gyro_bias_x/y/z` | 88, 92, 96 | float32 | ? | Jiroskop sapma tahmini (DatCon: `gb_*`); ±0.003 içinde yavaş değişiyor |
| `temperature` | 106 | int16 ÷ 100 | °C | IMU sıcaklığı ✈: açılışta 55, uçuşta 65'e çıkıp orada kalıyor |

Alan yerleşimi DatCon'daki `IMU_ATTI` (id 2048) tanımıyla aynı. Çözülmeyen byte'lar: 0–15 (GPS enlem/boylam, Tello'da 0), 100–105 (pusula, 0), 108 (0'dan 450'ye yavaşça artan bir sayı, anlamı bilinmiyor), 110 (ikinci bir sıcaklık: 33 → 44 °C), 118 (sayaç).

### 4.2 Optik akış odometrisi: `LogNewMvoFeedback` (id 29) — 5 Hz ✈

Drone'un alt kamera ve ToF ile kendi yaptığı konum/hız tahmini (bu drone'un çıktısı, bizim hesabımız değil).

| Alan | Payload byte | Ham tip | TelloPy dönüşümü | Birim | Not |
|---|---|---|---|---|---|
| `vel_x`, `vel_y`, `vel_z` | 2, 4, 6 | int16 | ÷ 1000 | **m/s** ✈ | Telde mm/s. Eskiden ÷100 yapılıyordu, değerler 10 kat büyüktü (§9.16) |
| `pos_x`, `pos_y`, `pos_z` | 8, 12, 16 | float32 | yok | **m** ✈ | **Dünya ekseninde** (x yaw 0°, y yaw +90°) ✈, **z aşağı** ✈ (inişte 1.83 → 3.06, yani 1.23 m iniş; yükseklik 13 dm ile uyumlu) |
| `height` | 68 | float32 | işareti çevrilir | **m** ✈ | Yerden yükseklik; ToF ile aynı (r = 1.00). Yerde 0.1 |
| `flags` | 76 | uint8 | yok | — | Geçerlilik bitleri (SMerrony/tello): 0x01, 0x02, 0x04 = hız x, y, z; 0x10, 0x20, 0x40 = konum y, x, z. Yerde 8, havada 127 ✈ |

Test uçuşunda görülenler ✈:
- **Yerde:** Konum (0.02, 0.01, 0.00) civarında sabit, hız 0.
- **Kalkışta:** Konum birden **(32.99, 54.84, 2.11)**'e sıçradı (ikinci uçuşta (−13.0, 16.6, 8.9)'a; yani sıçrama her seferinde farklı). Yani havadaki konumun başlangıç noktası anlamsız; mutlaka kalkıştan sonra sıfırlanmalı. `dji_tello_controller.py` bunu yapıyor.
- **Havada beklerken:** 15 s'de x/y ±0.1 m içinde kaldı.
- **İtişte:** 1.5 s'lik ileri itişte x +0.24 m arttı, geri itişte geri geldi. Sağa/sola dönüşte konum değişmedi.
- **İnişten sonra:** Konum yeniden yerdeki değere (0.02, 0.01) döndü.

Sıçramayan bir konum isteniyorsa `LogImuEx.pos_x/pos_y` (§4.6) aynı hareketi kalkış ve inişte sıçramadan veriyor ✈.

Güvenilirlik: IMU'ya göre 0.2–0.9 s gecikme ✔. Alt kamera zemini göremezse (karanlık, desensiz zemin) bozulması beklenir ~.

### 4.3 Gyro: `LogGyro` (id 1305) — 20 Hz, sadece havada ✈

| Alan | Payload byte | Tip | Not |
|---|---|---|---|
| `stages[0]` = (x, y, z) | 1, 5, 9 | 3 × float32 | Aynı gyronun 3 işlem aşaması |
| `stages[1]` | 13, 17, 21 | 3 × float32 | Aşamalar birbirinden ~10–20 ms gecikmeli ✔ |
| `stages[2]` | 25, 29, 33 | 3 × float32 | Hangisinin en ham olduğu bilinmiyor |

z ekseni IMU gyrosuyla 0.96–0.99 korelasyonlu ✔. x/y zayıf korelasyonlu, eksen sırası tahmin. Yaw hızı için en hızlı tepki veren kaynak stage 0 (~45 ms) ✔.

### 4.4 ToF mesafe: `LogTof` (id 16) — 5 Hz ✈

| Alan | Payload byte | Tip | Not |
|---|---|---|---|
| `distance` | 0–1 | int16 | Aşağı bakan sensörün ham değeri, **mm** ✈. Yerde 100 (ölçebildiği en küçük değer), havada 1241–1277 (yükseklik 13 dm) |
| `flag` | 2 | uint8 | Hep 1 görüldü |
| `counter` | 3 | uint8 | Her kayıtta 4 artar, 256'da başa döner; kayıp kayıt saymak için kullanılabilir |

### 4.5 Kontrol çıkışları: `LogControl` (id 1306) — 20 Hz, sadece motorlar çalışırken ✈

Yönelim kontrolcüsünün motorlardan istediği. Bu kaydın hiçbir kaynakta tanımı yok; aşağıdakiler iki uçuştan ✈.

| Alan | Payload byte | Tip | Not |
|---|---|---|---|
| `cols[0]` | 6 | int16 | Roll çıkışı. Sağa yatma hızına ters işaretli (düzeltici) |
| `cols[1]` | 8 | int16 | Pitch çıkışı. Burun yukarı hızına ters işaretli |
| `cols[2]` | 10 | int16 | Yaw çıkışı |
| `cols[3]` | 12 | int16 | İtki. Havada sabit dururken ~4000 (pil doluyken ~3400) |
| `cols[4..7]` | 14–20 | int16 | Aynı dördü bir daha; yalnızca inişte farklılaşıyor |

Byte 22'de sabit 0 ve 24'te sabit 1000 var (`cols`'a alınmıyor).

Bu dört çıkışın motorlara nasıl dağıldığı §4.6'daki `LogMotorCtrl`'de.

### 4.6 Sonradan çözülen kayıtlar (`EVENT_SAMPLE_RAW`)

Bu kayıtlar TelloPy'nin özgün hâlinde çözülmüyordu. İki gerçek uçuşun ham kayıtlarından çözüldüler:
- Her alan, anlamı bilinen bir sinyalle (IMU, ToF, gönderdiğimiz çubuk komutu, uçuş aşaması) üst üste oturtuldu.
- Tanımı olanlar ayrıca DatCon'un (DJI uçuş kaydı çözücüsü) kaynak koduyla karşılaştırıldı; sınıf adları oradan.
- İkinci uçuş (`kayitlar/paket_dinleme_20261111_143727/`, `tello_paket_dinle.py --ucus --eksen --elle 60`) her ekseni ayrı ayrı oynattı: yukarı/aşağı, sağa/sola kayma, ileri/geri, sağa/sola dönüş; ardından motorlar kapalıyken elle eğme, çevirme, kaldırma.

Hepsi `EVENT_SAMPLE_RAW` ile gelir; `data` aşağıdaki sınıflardan biridir (`isinstance` ile ayırın). Ham `payload` yine saklanır.

Eksenler: **hız, konum ve `lin_acc` dünya ekseninde**: x = yaw 0° yönü, y = yaw +90° yönü, z aşağı. Ham ivme ve jiroskop gövde ekseninde (x ileri, y sağa, z aşağı). Açılar: pitch burun yukarı +, roll sağ taraf aşağı +, yaw yukarıdan bakınca saat yönü +.

> **Düzeltme (üçüncü uçuş, `kayitlar/tellolink_20261111_195152/`):** İlk iki uçuşta hızların "x ileri, y sağa" olduğu sonucuna varılmıştı. O uçuşlarda drone yaw ≈ −12° dönüktü, yani dünya ekseni gövdeyle neredeyse çakışıyordu. Üçüncü uçuşta drone yaw 80° dönük kalktı: ileri itiş `vel_y` +0.36, sağa kayma `vel_x` −0.37 olarak geldi. Hız yaw ile döndürülünce gövdeye göre ileri +0.37, yana 0.01 m/s çıktı. IMU, nav (2064), MVO, osd ve FlightData hızlarının hepsi ve nav/MVO konumları böyle. `lin_acc_x/y` de dünya hızının türeviyle uyuşuyor (r = 0.7; gövdeyle ~0). Yaw'ın sıfır yönünü drone kendisi seçiyor (pusulası yok).

#### `LogOsdGeneral` (id 12) — 1.7 Hz. Drone'un kendi durum özeti

| Alan | Payload byte | Ham tip | Birim | Not |
|---|---|---|---|---|
| `height` | 16 | int16 ÷ 10 | m | Kalkış noktasına göre yükseklik (`FlightData.height` ile aynı) |
| `vel_x`, `vel_y`, `vel_z` | 18, 20, 22 | int16 ÷ 10 | m/s | 0.1 m/s adımlı ve sıfıra doğru yuvarlanmış; kaba. IMU hızıyla r = 0.92–0.98 |
| `pitch`, `roll`, `yaw` | 24, 26, 28 | int16 ÷ 10 | derece | IMU kuaterniyonundan hesaplananla r = 1.00. Elle öne eğince pitch −25°, sağa eğince roll +28° ✈ |
| `fly_mode` | 30 | uint8 | — | `FlightData.fly_mode` ile aynı: 6 sabit, 11 kalkış, 12 iniş |
| `tof_height` | 41 | uint8 ÷ 10 | m | Mesafe sensöründen yükseklik (yerde 0.1) |
| `fly_time` | 42 | uint16 ÷ 10 | s | Motorların çalıştığı süre |
| `yaw_rate` | 53 | int16 ÷ 10 | derece/s | DatCon'da yok (Tello'ya özgü son 6 byte'ta) |

Çözülmeyenler: 0–15 (GPS, 0), 31 (0 uçuştan önce, 1 havada, 2 inişten sonra), 32–39 (durum bitleri), 45–48 (sabit), 50 (ilk uçuşta inişten sonra 125).

#### `LogController` (id 1000) — 5 Hz. Uçuş kontrolcüsünün gördüğü çubuklar

| Alan | Payload byte | Tip | Not |
|---|---|---|---|
| `pitch` | 4 | float32 | İleri/geri çubuğu. Gönderilenin 0.90–0.97 katı okunuyor: 0.3 → 0.278, 0.25 → 0.227, 0.4 → 0.362, 0.5 → 0.485 ✈ |
| `roll` | 8 | float32 | Sağ/sol çubuğu |
| `yaw` | 12 | float32 | Dönüş çubuğu |
| `throttle` | 16 | float32 | Yukarı/aşağı çubuğu |
| `fly_mode` | 20 | uint8 | `FlightData.fly_mode` ile aynı |
| `motors_on` | 22 | uint8 | 1 = kalkıştan motorlar durana kadar |

Çözülmeyenler: 0 (sayaç), 26–28 (yükseklik ve uzaklık sınırı ~), 38–41 (kalkış ve inişte değişen istek/eylem numaraları).

#### `LogAircraftCondition` (id 1001) — 5 Hz

| Alan | Payload byte | Tip | Not |
|---|---|---|---|
| `flight_state` | 1 | uint8 | 0 yerde, 1 kalkıyor, 2 havada ✈ |
| `last_flight_state` | 2 | uint8 | Bir önceki durum |
| `landed` | 13 | uint8 | 1 = yerde ✈. `FlightData.em_ground`'un aksine gerçekten "yerde" demek (§9.14) |

#### `LogAttitudeControl` (id 1304) — 2.5 Hz, sadece motorlar çalışırken. Hedef ve gerçek yönelim

Hiçbir kaynakta tanımı yok; ad bizim.

| Alan | Payload byte | Tip | Birim | Not |
|---|---|---|---|---|
| `target_yaw`, `target_roll`, `target_pitch` | 2, 6, 10 | float32 | radyan | Kontrolcünün hedefi. `target_yaw` dönüş çubuğu ortadayken sabit kalıyor, çubuk itilince drone ile birlikte ilerliyor ✈ |
| `yaw`, `roll`, `pitch` | 22, 26, 30 | float32 | radyan | Gerçek yönelim; IMU kuaterniyonuyla r = 1.00 |

Byte 14–21 hedef roll/pitch'in kopyası.

#### `LogMotorCtrl` (id 1307) — 10 Hz, sadece motorlar çalışırken. Motor sürüşü

| Alan | Payload byte | Ham tip | Birim | Not |
|---|---|---|---|---|
| `pwm[0..3]` | 0, 2, 4, 6 | uint16 ÷ 100 | % | Yerde rölantide ~24, havada 55–65 ✈ |

Motor sırası: **ön sağ, ön sol, arka sol, arka sağ**. Bu, karıştırma katsayılarından çıktı: her motor, iki uçuşta da %1 içinde,

`pwm × 100 ≈ 0.9·itki ± 0.6·roll ± 0.6·pitch ± 0.85·yaw + 2400` (`LogControl.cols[0..3]`)

| Motor | roll | pitch | yaw |
|---|---|---|---|
| `pwm[0]` ön sağ | − | + | + |
| `pwm[1]` ön sol | + | + | − |
| `pwm[2]` arka sol | + | − | + |
| `pwm[3]` arka sağ | − | − | − |

Hangi çiftin "ön" ve hangisinin "sağ" olduğu, pitch ve roll hızına hangi motorların karşılık verdiğinden çıkarıldı ~; pervaneyi tek tek elle durdurarak doğrulanmadı.

#### `LogBattery` (id 1710) — 5 Hz

| Alan | Payload byte | Ham tip | Birim | Not |
|---|---|---|---|---|
| `voltage` | 0 | float32 ÷ 1000 | V | Yerde 4.09, havada 3.54, inince 4.03 ✈. `FlightData.drone_fly_time_left` (mV) ile aynı değer |

#### `LogImuEx` (id 2064) — 10 Hz. Kontrolcünün kullandığı konum ve hız

| Alan | Payload byte | Tip | Birim | Not |
|---|---|---|---|---|
| `vel_x`, `vel_y`, `vel_z` | 0, 4, 8 | float32 | m/s | `LogImuAtti.vg_*` ile aynı sayılar |
| `pos_x`, `pos_y` | 12, 16 | float32 | m | **Kalkışta ve inişte sıçramayan konum** ✈. MVO ile aynı hareketi gösteriyor (r = 0.99–1.00, ölçek 0.97) |
| `pos_z` | 20 | float32 | m | `−LogImuAtti.baro` |
| `tof_vel` | 24 | float32 | m/s | Yüksekliğin değişim hızı; yükselirken − |
| `height` | 28 | float32 | m | Yerden yükseklik; ToF ile r = 1.00 |
| `flags` | 56 | uint16 | — | 1 yerde, 84 havada, 68 yatay hareket ederken ✈; bitlerin anlamı bilinmiyor |
| `counter` | 58 | uint16 | — | |

`pos_x`/`pos_y` hakkında bilinmesi gerekenler ✈:
- Açılışta sıfır olmayabilir: ilk uçuşta 0'dan başladı, ikincisinde (1.77, 3.14)'ten. Yani yine bir başlangıç değeri çıkarmak gerekir; ama bu değer kalkışta değişmiyor.
- Drone elle kaldırılınca (0, 0)'a sıfırlandı.
- 1.5 s'lik itişlerde (ikinci uçuş, yaw ≈ −12°): x +0.5 m, y +0.45 m; karşı itişle geri geldi. Konum da dünya ekseninde.

#### `LogAttiMini` (id 2208) — 10 Hz

| Alan | Payload byte | Tip | Birim | Not |
|---|---|---|---|---|
| `q0`…`q3` | 0, 4, 8, 12 | float32 | — | İkinci bir yönelim kuaterniyonu; yaw'ı IMU'nunkinden yavaşça uzaklaşıyor |
| `altitude` | 16 | float32 | m | Barometre irtifası (`LogImuAtti.baro` gibi) |
| `vel_z` | 20 | float32 | m/s | Dikey hız, aşağı + |
| `acc_z` | 24 | float32 | m/s² | Dikey ivme; `LogImuAtti.lin_acc_z` ile r = 1.00 |

### 4.7 Hâlâ çözülmeyen kayıtlar (`EVENT_SAMPLE_RAW`)

Bunlar `LogRecord` olarak, sadece `record_id`, `tick` ve ham `payload` ile gelir.

| id | Sıklık | Payload | Ne zaman | Bilinen |
|---|---|---|---|---|
| 1200 | 1 Hz | 24 | motorlar çalışırken | Dikey kontrol. Byte 1–2: yükseklik tutma açık (2, 1) / kapalı (0, 0; yukarı/aşağı çubuğu itiliyken) ✈. float32 @3: tutulacak barometre irtifası ✈ |
| 1202 | 1 Hz | 33 | motorlar çalışırken | Dikey hız kontrolü. Byte 0: 2 yükseklik tutuyor, 1 hız izliyor. int16 @1, 3, 5: istenen dikey hız (cm/s, yukarı +); @7: ölçülen ✈ |
| 1203 | 1 Hz | 7 | motorlar çalışırken | int16 @3: dikey ivme ~; int16 @5: itki (`LogControl.cols[3]` ile aynı) ✈ |
| 1300 | 1 Hz | 137 | motorlar çalışırken | Yatay kontrol olmalı ~; içinde yaw (radyan) ve ToF'u izleyen alanlar var |
| 1303 | 0.5 Hz | 64 | motorlar çalışırken | Bilinmiyor |
| 10085 | 5 Hz | 80 | hep | DatCon: `ns_data_debug`, 20 adsız float32. Sadece @44, 48, 52 dolu; yavaş kayan küçük değerler |
| 10086 | 5 Hz | 4 | hep | DatCon: `ns_data_component`, bit maskesi. Byte 0: 0x00 yerde, 0x30 kalkışta, 0xF0 havada ✈ |
| 10100 | 2.5 Hz | 21 | hep | DatCon'daki tanım (`RecAirComp`) Tello'ya uymuyor. Beş float32; yerde 0, havada küçük değerler; sonuncusu 220–241 |
| 1002 | 0.5 Hz | 27 | hep | DatCon: `serial_api_inputs` (SDK komutları). Byte 19 = 0xFF dışında hep 0 |

1200–1306 arasındaki kayıtların hiçbir açık kaynakta tanımı yok (DatCon, TelloLib, SMerrony/tello tarandı).

---

## 5. Diğer drone mesajları

| Mesaj | Olay | `data` | Tip | Not |
|---|---|---|---|---|
| Wi-Fi (`0x001A`) | `EVENT_WIFI` | ham byte'lar | bytes | 2 byte ✈, saniyede bir. `[0]` sinyal gücü → `drone.wifi_strength` (uçuş boyunca 90 ✈), `[1]` parazit ~ → `drone.wifi_disturb` (hep 0 ✈); ikisi de `FlightData`'ya kopyalanır |
| Işık (`0x0035`) | `EVENT_LIGHT` | ham byte'lar | bytes | 1 byte ✈, 2 s'de bir. `[0]` ışık seviyesi ~ → `drone.light_strength` ve `FlightData.light_strength`. Aydınlık odada hep 0 ✈; muhtemelen "ışık yetersiz" uyarısı ~ |
| Günlük başlığı (`0x1050`) | `EVENT_LOG_HEADER` | ham byte'lar | bytes | Bağlanınca gelir; TelloPy kendisi onaylar |
| Günlük ayarı (`0x1052`) | `EVENT_LOG_CONFIG` | ham byte'lar | bytes | 2 s'de bir, hep aynı 58 byte ✈; çözülmez |
| Zaman (`0x0046`) | `EVENT_TIME` | paketin içeriği | bytes | Drone 2.5 s'de bir **saati soruyor**, içerik boş ✈. TelloPy artık saati gönderiyor (§9.15) |
| Kalibrasyon (`0x005B`) | `EVENT_CALIBRATION_STATUS` | `CalibrationStatus` | | `step_mask` (0→0x3F), `progress` (0–100), `steps_done`, `done` |
| Fotoğraf (`0x0062`/`0x0063`) | `EVENT_FILE_RECEIVED` | JPEG byte'ları | bytes | `take_picture()` sonrası |
| İrtifa/eğim/pil eşiği yanıtları | — | — | — | Olay olarak yayınlanmaz, sadece log'a yazılır |
| SSID / şifre | `get_ssid()` / `get_password()` dönüşü | metin | str | Bloklayan çağrı |

---

## 6. Görüntü

| Özellik | Değer |
|---|---|
| Kaynak | Drone, UDP port 6038 |
| Biçim | Ham H.264 Annex-B, sadece I ve P kareler ✔ |
| Çözünürlük | 960×720 (4:3, varsayılan) veya 1280×720 (16:9, `set_video_mode(zoom=True)`) |
| Kare hızı | **32 kare/s** ✈ (kare başına ~5 UDP paketi, çoğu 1460 byte; saniyede ~277 paket) |
| Zaman damgası | **Görüntüde yok** ✔. Sadece her UDP paketinin `recv_time`'ı var; çözülen karenin kendi zamanı yok |
| Paket başlığı | 2 byte: `[0]` kare sıra no (0–255), `[1] & 0x7F` kare içindeki paket no. TelloPy bununla kaybı sayar (`drone.video_data_loss`) |
| Okuma | `av.open(drone.get_video_stream())` → `decode(video=0)` → `frame.to_ndarray(format="bgr24")` |
| Ham paket | `EVENT_VIDEO_FRAME` (`data` = başlıksız H.264 parçası) |
| Güvenilirlik | UDP kaybında kareler bir sonraki I-kareye kadar bozuk gelir. Bağlantı başındaki ilk kareler de bozuk gelir; test uçuşunda ilk `av.open` 5. saniyede "Invalid data" hatası verdi ✈, yeniden açmak gerekir. Görüntü durursa okuma bekler; akış sadece bağlantı kopunca biter, yeniden bağlanınca tekrar açılır (§9.5) |

---

## 7. Komut yanıtları

| Olay | `data` | Alanlar | Not |
|---|---|---|---|
| `EVENT_SAMPLE_COMMAND_ACK` | `CommandSample` | `name`, `cmd`, `seq`, `send_time` (bizim saatimiz), `recv_time` (yanıtın geldiği an), `rtt` (s), `ack_payload` | Kalkış/iniş/ayar komutlarına drone'un onayı |
| `EVENT_SAMPLE_COMMAND_TIMEOUT` | `CommandSample` | aynı, `recv_time = None` | 1.5 s içinde yanıt gelmedi |

Ölçülmüş gidiş-dönüş ✔: min 5–6 ms, medyan 44 ms, ortalama ~53 ms, %95 ~124 ms, en çok ~220 ms; ~%2 yanıtsız.

> **Drone'dan gelmeyen:** `EVENT_SAMPLE_STICK` (`StickSample`), **bizim** gönderdiğimiz çubuk komutunun kaydıdır. Komutlar alınan her pakette bir kez gönderilir: medyan 48 ms aralık, %95 ~125 ms, en çok 0.3–0.8 s ✔.

---

## 8. Güvenilirlik notları

1. **Paket kaybı normal.**
   - **IMU:** 100 ms aralıkların %19–23'ü eksik ✔.
   - **Gyro:** Aralıkların %17–20'si >75 ms, ~%4'ü >150 ms, en uzunu 0.3–0.8 s ✔.
   - **Sonuç:** Sabit örnekleme sıklığı varsaymayın; `tick` kullanın.
2. **Bağlantı başındaki eski kayıtlar:** Drone önce 3 eski IMU kaydı gönderiyor ✔ ✈ (test uçuşunda tick 8.09 M → 8.56 M, sonra 174 M). Bunların tick'i, açıldıktan ~3.5 s sonraya ait; sonra tick onlarca saniye ileri atlıyor. İlk kayıtları atlayın. TickClock bunu kendisi eler.
3. **`recv_time` ≠ ölçüm zamanı:** Paketteki eski kayıtlar daha uzun beklemiş olur ✔. Hassas zaman için `tick` ya da §2.2 kullanın.
4. **MVO gecikmesi** 0.2–0.9 s ve oynak ✔. Anlık kontrol için tek başına uygun değil.
5. **Birimi bilinmeyenler:** ToF `distance`, IMU `acc`/`gyro`, `vg_*`, FlightData hızları, `fly_mode` kodları.
6. **`EVENT_LOG_DATA` tekrar verir:**
   - `data` her seferinde aynı `LogData` nesnesi.
   - `data.mvo` / `data.imu`, o pakette yoksa eski kaydı gösterir.
   - Paket bozuk çözülse bile olay yine tetiklenir.
   - Bu yüzden yeni veri için `EVENT_SAMPLE_*` kullanın.
7. **Bağlantı kopması:** 2 s paket gelmezse TelloPy kopmuş sayar ve kendisi yeniden bağlanır.

---

## 9. Kütüphanede bulunan ve düzeltilen hatalar

9.1–9.12 kod okunarak, 9.13–9.16 test uçuşunun ham paketlerinden bulundu. Hepsi `TelloPy/` içinde düzeltildi; her düzeltmenin testi var.
"Etki" sütunu, hatanın düzeltmeden önce veri okurken size nasıl dokunduğunu gösteriyor.

| # | Hata | Yer | Etki | Durum |
|---|---|---|---|---|
| 9.1 | `int16` 256–32767 arası değerleri bozuyordu | `utils.py`, `int16` | **Yüksek**: FlightData'da 7 alan | ✔ Düzeltildi |
| 9.2 | Gönderilen paketlerdeki saat hep program açılış saatiydi | `protocol.py`, `Packet.add_time` | Orta: drone'a yanlış saat gidiyordu | ✔ Düzeltildi |
| 9.3 | Işık ve Wi-Fi paraziti hiç doldurulmuyordu | `tello.py`, Wi-Fi/ışık/uçuş mesajları | Orta: alanlar hep 0'dı | ✔ Düzeltildi |
| 9.4 | `EVENT_TIME` yanlış byte'ları veriyordu | `tello.py`, zaman mesajı | Düşük | ✔ Düzeltildi |
| 9.5 | Bağlantı kopunca görüntü geri gelmiyordu; 5 s duraklama akışı bitiriyordu; okuma verimsizdi | `video_stream.py` | **Yüksek** (uzun uçuşta) | ✔ Düzeltildi |
| 9.6 | `bytearray` gelirse günlük çözümü bozuluyordu | `protocol.py`, `LogData.update` | Tetiklenmiyordu | ✔ Düzeltildi |
| 9.7 | Kayıtlarda ve paketlerde checksum/CRC kontrol edilmiyordu | `protocol.py`, `tello.py` | Düşük | ✔ Düzeltildi ✈ |
| 9.8 | IMU CSV başlığında yazım hatası | `protocol.py`, `LogImuAtti.format_cvs_header` | Düşük | ✔ Düzeltildi |
| 9.9 | `Packet.get_time` milisaniyeyi mikrosaniye diye veriyordu | `protocol.py`, `Packet.get_time` | Kullanılmıyordu | ✔ Düzeltildi |
| 9.10 | `record_log_data()` Windows'ta yanlış klasöre yazıyordu | `tello.py`, `record_log_data` | Düşük | ✔ Düzeltildi |
| 9.11 | Kayan noktalar bilgisayarın byte sırasıyla okunuyordu | `protocol.py`, IMU/MVO çözümü | Bilgisayarda yok (önleyici) | ✔ Düzeltildi |
| 9.12 | 4 test Windows'ta ya da aralıklı düşüyordu | `tests/offline/contract/` | Testler | ✔ Düzeltildi |
| 9.13 | İki pakete bölünen günlük kayıtları kayboluyordu | `protocol.py`, `LogData.update` | Orta: günlük paketlerinin %2'si ✈ | ✔ Düzeltildi |
| 9.14 | `em_ground` "yerde" sanılıyordu | bizim kodumuz | Orta: iniş algılanamıyordu ✈ | ✔ Düzeltildi |
| 9.15 | Drone'un saat isteklerine yanıt verilmiyordu | `tello.py`, zaman mesajı | Düşük | ✔ Düzeltildi |
| 9.16 | MVO hızı 10 kat büyük çıkıyordu | `protocol.py`, `LogNewMvoFeedback` | Orta | ✔ Düzeltildi ✈ |

### 9.1 `int16` hatası

**Neden hataydı:** 16 bitlik bir sayının negatif olup olmadığını **en üst bit** (`0x8000`) belirler. Kod ise yüksek byte'ın **sıfır olmamasına** bakıyordu.
- Sonuç olarak 256'dan büyük her pozitif değer negatif çıkıyordu: 300 → −65236, 3800 → −61736 (çalıştırarak doğrulandı).
- Etkilenen alanlar: `height`, `north_speed`, `east_speed`, `ground_speed`, `fly_time` (~25 s sonra), `drone_battery_left` (hep), `drone_fly_time_left`.

**Düzeltme:** İşaret artık üst bitten okunuyor. Test, −32768 ile 32767 arasındaki sınır değerleri kontrol ediyor.

### 9.2 Gönderilen saat donuk kalıyordu

**Neden hataydı:** `def add_time(self, time=datetime.datetime.now())` satırında Python, varsayılan değeri fonksiyon her çağrıldığında değil, **modül yüklenirken bir kez** hesaplar.
- Bu yüzden her pakete TelloPy'nin import edildiği anın saati yazılıyordu. 1.5 s arayla oluşturulan iki paketin byte'ları aynıydı.
- Etkilenenler: bağlanınca drone'a gönderilen zaman komutu ve her çubuk paketi.
- Okuduğunuz veriler (`tick`, `recv_time`) bundan etkilenmiyordu.

**Düzeltme:** Varsayılan değer `None` yapıldı; saat her çağrıda alınıyor.

### 9.3 Işık ve Wi-Fi paraziti doldurulmuyordu

**Neden hataydı:** Drone bu değerleri ayrı mesajlarla gönderiyor, ama TelloPy onları `FlightData`'ya hiç aktarmıyordu.
- **Işık:** Mesaj geldiğinde sadece ham byte'lar `EVENT_LIGHT` ile yayınlanıyor, `light_strength` alanına hiçbir yer yazmıyordu.
- **Wi-Fi:** Mesajdan sadece 1. byte (güç) okunuyor, 2. byte (parazit ~) atılıyordu.

**Düzeltme:** Son değerler `drone.light_strength` ve `drone.wifi_disturb` olarak tutuluyor ve her `FlightData`'ya kopyalanıyor (`wifi_strength` zaten böyle çalışıyordu).
- Bu byte'ların gerçekten ışık ve parazit olduğu topluluk bilgisi (~); gerçek drone ile doğrulanacak.
- `smart_video_exit_mode` 0 kalıyor, çünkü bu bilgiyi taşıyan mesaj TelloPy'de hiç işlenmiyor.

### 9.4 `EVENT_TIME` yanlış byte'ları veriyordu

**Neden hataydı:** Paket yapısında 7–8. byte'lar **paket sıra numarasıdır**; içerik 9. byte'tan başlar. Kod `data[7:9]` gönderiyordu, yani olayla gelen değer zaman değil sıra numarasıydı.

**Düzeltme:** Artık içerik (`data[9:-2]`, CRC hariç) gönderiliyor.

### 9.5 Görüntü akışı

**Neden hataydı:**
1. **Kopmadan sonra geri gelmiyordu.**
   - `VideoStream`, bağlantı kopunca `closed = True` yapıyordu, ama bunu geri alan kod yoktu.
   - `get_video_stream()` hep aynı akış nesnesini döndürdüğü için, yeniden bağlandıktan sonra `av` kapalı akıştan okuyup akışı bitmiş sayıyordu.
2. **5 saniyelik duraklama akışı bitiriyordu.** `read()`, 5 s veri gelmezse boş dönüyordu. `av` boş okumayı "akış bitti" diye yorumladığı için, kısa bir görüntü kesintisi de çözmeyi bitiriyordu.
3. **Verimsizdi.**
   - Her okumada byte'lar `data = data + parça` ile tek tek ekleniyordu; parça sayısı arttıkça süre karesel büyür.
   - Kuyruğun başından silme (`del list[0]`) her seferinde bütün listeyi kaydırıyordu.
   - İstenenden büyük bir parça hiç verilemiyor ve akışı kilitliyordu.

**Düzeltme:**
- Bağlantı geri gelince akış yeniden açılıyor; ilk karenin başından okumaya başlıyor.
- `read()` bağlantı sürdükçe bekliyor; sadece bağlantı koparsa ya da `quit()` çağrılırsa bitiyor.
- Kuyruk `deque` oldu, birleştirme `b''.join` ile yapılıyor ve büyük parçalar bölünerek veriliyor.
- `dji_tello_controller.py`'deki geçici çözüm artık gerekmiyor ama zararı da yok.

### 9.6 `bytearray` → `str`

**Neden hataydı:** Python 3'te `str(bytearray(...))` byte'ları değil, `"bytearray(b'...')"` **metnini** üretir; ardından çözümleme çöker. Python 2'den kalma bir satırdı. TelloPy kendisi `bytes` verdiği için tetiklenmiyordu, ama kayıtlı paketleri `bytearray` olarak verirseniz çökerdi.

**Düzeltme:** `bytes(data)`.

### 9.7 Bütünlük kontrolü

**Neden hataydı:** Kayıt başlığındaki checksum okunuyor ama kullanılmıyordu; kayıt sonundaki ve paket sonundaki CRC hiç kontrol edilmiyordu. Bozuk bir kayıt geçerliymiş gibi sayıya çevrilebilirdi.

**Doğrulama ✈:** Algoritmalar test uçuşunun ham paketleriyle denendi:
- **Paket:** Uzunluk alanı, ilk 3 byte'ın crc8'i ve son 2 byte'taki crc16; 2364 paketin hepsinde doğru.
- **Kayıt:** İlk 3 byte'ın crc8'i (7405/7405 doğru) ve son 2 byte'taki crc16. CRC16'da 8 "hata" görünüyordu; bunların hepsinin iki pakete bölünmüş kayıtlar olduğu anlaşıldı (§9.13).

**Düzeltme:**
- **Paket:** Uzunluğu ya da CRC'si yanlış paket atılıyor (`drone.bad_packets` sayıyor).
- **Kayıt:** crc16'sı yanlış kayıt atılıyor (`LogData.crc_errors`). Başlık crc8'i, kayıp bir paketten sonra bir sonraki kaydın başını bulmak için kullanılıyor (`LogData.skipped_bytes`).
- **Sahte drone:** Artık doğru checksum'lı kayıt üretiyor.

### 9.8 IMU CSV başlığı

**Neden hataydı:** Sütun adı `imu.q3` yerine `" self.q3"` yazılmıştı. **Düzeltme:** Ad düzeltildi.

### 9.9 `Packet.get_time`

**Önceki raporda yanlış yazmıştım:** `buf[8]` okuması hata değil. `add_time`, milisaniyenin alt ve üst byte'ını iki ayrı int16 olarak [6] ve [8]'e yazıyor; `get_time` de onları doğru okuyor.

**Asıl hata:** Okunan milisaniye, `datetime`'a **mikrosaniye** olarak veriliyordu; 678 ms, 0.678 ms oluyordu. **Düzeltme:** ×1000.
Kütüphanede çağrılmıyor; kendiniz kullanmadıkça etkisi yoktu.

### 9.10 `record_log_data()` klasörü

**Neden hataydı:** Varsayılan yol `os.getenv('HOME')` ile kuruluyordu. Windows'ta `HOME` çoğunlukla tanımlı olmadığından yol `None/Documents/...` oluyordu.

**Düzeltme:** `os.path.expanduser('~')`.

### 9.11 Kayan nokta byte sırası

**Neden hataydı:** IMU ve MVO kayan noktaları `'fff'` biçimiyle, yani bilgisayarın kendi byte sırasıyla çözülüyordu. Drone little-endian gönderiyor. Bilgisayarlarda (x86/ARM) sonuç aynıydı, ama big-endian bir sistemde yanlış çıkardı.

**Düzeltme:** `'<3f'`; diğer alanlar zaten böyleydi.

### 9.12 Testler

- **Windows'ta dosya kilidi:** İki Recorder testi kaydı durduruyor ama dosyayı kapatmıyordu. Windows açık dosyayı silemediği için test sonunda hata veriyordu. Artık test sonunda kapatılıyor.
- **Aralıklı düşen kalibrasyon testleri:** Sahte drone, kütüphanenin "durum ne?" sorusunu aynen geri yansıtıyor. Test bazen gerçek yanıt yerine bu boş yansımayı ilk yanıt sanıyordu. Artık gönderilen durumu arıyor.
- **Yeni testler:** `tests/offline/detail/test_decoding.py` (14 test) düzeltmelerin hepsini kapsıyor.

Sonuç: 144/144 test geçiyor.

### 9.13 İki pakete bölünen günlük kayıtları ✈

**Neden hataydı:** Drone günlük akışını en fazla ~1000 byte'lık paketlere, kayıt sınırına bakmadan bölüyor. Bir kaydın başı bir pakette, sonu sonraki pakette kalabiliyor. TelloPy her paketi bağımsız çözdüğü için:
- Bölünen kaydı kaybediyordu.
- Sonraki paketin başını "bozuk veri" sayıp o paketteki **tüm** kayıtları atıyordu.

Test uçuşunda 1372 günlük paketinin 26'sında (%2) bu oldu.

**Düzeltme:** Paketin sonunda yarım kalan kayıt saklanıyor ve sonraki paketle tamamlanıyor. Kayıp bir paketten sonra bir sonraki geçerli kayıt başlığı aranıyor. Aynı kayıt yeniden çözüldüğünde 7410 yerine 7426 kayıt çıktı; hiç hata ve CRC hatası kalmadı ✈.

### 9.14 `em_ground` "yerde" demek değil ✈

**Neden hataydı:** Alanın adı yüzünden "1 = yerde" sanılıyordu. Test uçuşunda ise sadece kalkışta, motorlar dönmeye başlarken ~0.5 s 1 oldu; inişten sonra hiç 1 olmadı. Bu yüzden `tello_paket_dinle.py` inişi algılayamayıp "iniş doğrulanamadı" yazdı (iniş aslında olması gerektiği gibi gerçekleşmişti).

**Düzeltme:** TelloPy'de değil bizim kodumuzda. `tello_paket_dinle.py` ve `dji_tello_controller.py` artık yerde olmayı `em_sky = 0` ve `em_open = 0` (motorlar durmuş) ile anlıyor.

### 9.15 Saat isteklerine yanıt

**Neden hataydı:** Drone, telemetrisiyle aynı tipte (0x88) boş zaman paketleriyle 2.5 s'de bir saati soruyor ✈. TelloPy saati sadece bağlanırken bir kez gönderiyordu; sonraki istekler yanıtsız kalıyordu.

**Düzeltme:** Böyle bir istek gelince saat gönderiliyor (Go dilindeki Tello sürücüsü de böyle yapıyor). İstek tipine (0x88) bakıldığı için kendi gönderdiğimizin yansımasına yanıt verip döngüye girmiyor. Bunun drone'da bir şeyi değiştirip değiştirmediği bir sonraki kayıtta görülecek.

### 9.16 MVO hızının birimi ✈

**Neden hataydı:** Hız telde mm/s olarak geliyor; TelloPy 100'e bölüyordu, değerler gerçeğin 10 katıydı. Uçuşta iki yerden doğrulandı:
- **İleri itiş:** Konum 0.24 m değişirken hız "1.18" çıkıyordu. Gerçek 0.118 m/s.
- **İniş:** ToF'a göre ~0.4 m/s inilirken hız "6.37" çıkıyordu. Gerçek 0.64 m/s.

**Düzeltme:** 1000'e bölünüyor, değerler artık m/s.

### Açık kalanlar (gerçek drone ile)

| Konu | Neden bekliyor |
|---|---|
| Wi-Fi 2. byte ve ışık byte'ının anlamı | İkinci uçuşta alt kamera 12 s elle kapatıldı: ışık byte'ı yine 0 kaldı ✈. Bu firmware'de ışık değeri dolmuyor gibi; hiçbir kaynakta ölçeği de yazmıyor. Wi-Fi 2. byte da hep 0 |
| Günlük kayıtlarının gecikmesi | İkinci uçuşta `LogController`'daki çubuk değeri, komutu gönderdiğimiz andan 1.1–1.6 s sonraki tick'te göründü ✈. Bu gecikmenin günlük akışından mı, zaman eşlemesinden mi geldiği ayrıştırılmadı |
| Görüntünün ilk açılışta "Invalid data" vermesi | Bir sonraki kayıtta kare başlarının ilk byte'ları da kaydedilecek; akışın SPS/PPS olmadan mı başladığına bakılacak |
| 9 çözülmeyen kayıt türü (§4.7) | Ham paketler kayıtlı. 1300, 1303, 10085 ve 10100 için elde ipucu az |
| Motor sırası | Karıştırma işaretlerinden çıkarıldı (§4.6); pervaneyi tek tek durdurarak doğrulanmadı |
| **Çubuk komutu zamanlaması** (verimsizlik) | Komutlar ayrı bir zamanlayıcıyla değil, drone'dan paket geldikçe gönderiliyor. Bu yüzden aralıklar düzensiz: medyan 48 ms, en uzun 0.3–0.8 s ✔ (bizim uçuşumuzda en uzun 117 ms ✈). Sabit hızlı ayrı bir gönderici daha doğru olur, ama uçuş davranışını değiştirdiği için ancak uçuş testiyle yapılmalı. Öneri olarak bırakıldı, yapılmadı. |

---

## 10. Tüm verileri okuma örneği

Aşağıdaki program drone'dan gelen **her** veriyi okur, son değerleri saklar ve saniyede bir yazdırır. Drone kalkmaz.
Kendi kodunuza istediğiniz bölümü kopyalayın; her bölüm kendi başına çalışır.

Nasıl okunur:
- **Olay fonksiyonları:** Hepsi `(event, sender, data, recv_time, **args)` alır. `data` paketin çözülmüş hali, `recv_time` varış anı.
- **Thread:** Fonksiyonlar TelloPy'nin alım thread'inde çalışır. İçlerinde sadece değeri saklayın, işi ana döngüde yapın.
- **`connect()` sırası:** Abonelikleri `connect()`'ten **önce** yapın, ilk paketler kaçmasın.

```python
import threading
import time

import tellopy
from tellopy import Container, ImuContainer, GyroContainer, TickClock, Retimer


# ---------------------------------------------------------------------------
# 0) Yardımcılar
# ---------------------------------------------------------------------------
son = {}                    # ad -> (değer, recv_time)
kilit = threading.Lock()


def sakla(ad, deger, recv_time):
    with kilit:
        son[ad] = (deger, recv_time)


# ---------------------------------------------------------------------------
# 1) Uçuş durumu: FlightData (~10 Hz, tick YOK, sadece recv_time)
# ---------------------------------------------------------------------------
def ucus_verisi(event, sender, data, recv_time, **args):
    sakla("ucus", {
        "yukseklik_dm": data.height,
        "hiz_x": data.north_speed,              # dünya x (yaw 0° yönü), gövdeye göre değil
        "hiz_y": data.east_speed,               # dünya y (yaw +90° yönü)
        "hiz_asagi": data.ground_speed,         # adı "yer hızı" ama dikey hız, aşağı +
        "ucus_suresi": data.fly_time,
        "pil_yuzde": data.battery_percentage,
        "pil_mv": data.drone_fly_time_left,     # adı "kalan uçuş" ama pil gerilimi (mV)
        "havada": data.em_sky, "yerde": data.em_ground, "motor_acik": data.em_open,
        "hover": data.drone_hover, "pil_dusuk": data.battery_low, "pil_kritik": data.battery_lower,
        "imu_ok": data.imu_state, "baro_ok": data.pressure_state, "alt_kamera_ok": data.down_visual_state,
        "ruzgar": data.wind_state, "ucus_modu": data.fly_mode, "kamera": data.camera_state,
        "motor_durumu": data.electrical_machinery_state, "sicaklik_uyari": data.temperature_height,
        "imu_kalibrasyon": data.imu_calibration_state,
        # Bu üçü ayrı mesajlardan (EVENT_WIFI / EVENT_LIGHT) gelen son değerlerin kopyası:
        "wifi_guc": data.wifi_strength, "wifi_parazit": data.wifi_disturb, "isik": data.light_strength,
    }, recv_time)
    # smart_video_exit_mode: hiç doldurulmaz (hep 0).


# ---------------------------------------------------------------------------
# 2) Uçuş günlüğü kayıtları (her kayıtta tick VAR)
# ---------------------------------------------------------------------------
# EVENT_SAMPLE_* her kayıt için bir kez çağrılır; data, o kaydın kendisidir
# (yeni bir nesne, sonradan değişmez; referansını saklamak güvenli).
def imu(event, sender, data, recv_time, **args):
    sakla("imu", {
        "tick": data.tick,
        "ivme": (data.acc_x, data.acc_y, data.acc_z),
        "gyro": (data.gyro_x, data.gyro_y, data.gyro_z),
        "kuaterniyon": (data.q0, data.q1, data.q2, data.q3),        # q0 = w
        "dogrusal_ivme": (data.lin_acc_x, data.lin_acc_y, data.lin_acc_z),
        "vg": (data.vg_x, data.vg_y, data.vg_z),                    # anlamı bilinmiyor
    }, recv_time)


def mvo(event, sender, data, recv_time, **args):
    sakla("mvo", {
        "tick": data.tick,
        "konum": (data.pos_x, data.pos_y, data.pos_z),
        "hiz": (data.vel_x, data.vel_y, data.vel_z),
    }, recv_time)


def gyro(event, sender, data, recv_time, **args):
    sakla("gyro", {"tick": data.tick, "asamalar": data.stages}, recv_time)


def tof(event, sender, data, recv_time, **args):
    sakla("tof", {"tick": data.tick, "mesafe": data.distance, "sayac": data.counter}, recv_time)


def kontrol(event, sender, data, recv_time, **args):
    sakla("kontrol", {"tick": data.tick, "sutunlar": data.cols}, recv_time)


def diger_kayitlar(event, sender, data, recv_time, **args):
    # Sonradan çözülen kayıtlar (§4.6) da buradan gelir; türünü isinstance ile ayırın.
    if isinstance(data, tellopy.LogImuEx):              # sıçramayan konum, hız, yükseklik (10 Hz)
        sakla("konum2", {"tick": data.tick, "x": data.pos_x, "y": data.pos_y, "yukseklik": data.height,
                         "vx": data.vel_x, "vy": data.vel_y, "vz": data.vel_z}, recv_time)
    elif isinstance(data, tellopy.LogMotorCtrl):        # motor sürüşü, % (10 Hz, motorlar çalışırken)
        sakla("motorlar", {"tick": data.tick, "pwm": data.pwm}, recv_time)
    elif isinstance(data, tellopy.LogController):       # drone'un gördüğü çubuklar (5 Hz)
        sakla("cubuklar", {"tick": data.tick, "pitch": data.pitch, "roll": data.roll, "yaw": data.yaw,
                           "gaz": data.throttle, "motor_acik": data.motors_on}, recv_time)
    elif isinstance(data, tellopy.LogOsdGeneral):       # durum özeti: açılar derece olarak hazır (1.7 Hz)
        sakla("ozet", {"tick": data.tick, "pitch": data.pitch, "roll": data.roll, "yaw": data.yaw,
                       "yaw_hizi": data.yaw_rate, "ucus_suresi": data.fly_time}, recv_time)
    elif isinstance(data, tellopy.LogAttitudeControl):  # hedef ve gerçek yönelim, radyan (2.5 Hz)
        sakla("yonelim_hedefi", {"tick": data.tick, "hedef_yaw": data.target_yaw, "hedef_roll": data.target_roll,
                                 "hedef_pitch": data.target_pitch}, recv_time)
    elif isinstance(data, tellopy.LogBattery):          # pil gerilimi, V (5 Hz)
        sakla("pil", {"tick": data.tick, "volt": data.voltage}, recv_time)
    elif isinstance(data, tellopy.LogAircraftCondition):
        sakla("durum", {"tick": data.tick, "ucus_durumu": data.flight_state, "yerde": data.landed}, recv_time)
    elif isinstance(data, tellopy.LogAttiMini):
        sakla("dikey", {"tick": data.tick, "irtifa": data.altitude, "vz": data.vel_z, "az": data.acc_z}, recv_time)
    else:
        # Çözülmemiş kayıt türleri (§4.7): sadece id, tick ve ham byte'lar.
        sakla(f"kayit_{data.record_id}", {"tick": data.tick, "ham": data.payload}, recv_time)


# ---------------------------------------------------------------------------
# 3) Diğer drone mesajları (tick YOK)
# ---------------------------------------------------------------------------
def wifi(event, sender, data, recv_time, **args):
    # data = ham byte'lar. [0] sinyal gücü, [1] parazit ~ (drone.wifi_strength / wifi_disturb'e de yazılır).
    sakla("wifi", {"guc": data[0], "parazit": data[1] if len(data) > 1 else None}, recv_time)


def isik(event, sender, data, recv_time, **args):
    # [0] ışık seviyesi ~ (drone.light_strength'e de yazılır).
    sakla("isik", data[0], recv_time)


def gunluk_basligi(event, sender, data, recv_time, **args):
    sakla("gunluk_basligi", bytes(data), recv_time)     # bağlanınca bir kez; firmware metni içerir


def komut_yaniti(event, sender, data, recv_time, **args):
    # data = CommandSample: name, send_time, recv_time, rtt (s), ack_payload
    sakla(f"yanit_{data.name}", {"rtt_ms": data.rtt * 1000, "ham": data.ack_payload}, recv_time)


def komut_yanitsiz(event, sender, data, recv_time, **args):
    sakla(f"yanit_{data.name}", "YANIT YOK", recv_time)


def kalibrasyon(event, sender, data, recv_time, **args):
    sakla("kalibrasyon", {"ilerleme": data.progress, "adim": data.steps_done}, recv_time)


def dosya(event, sender, data, recv_time, **args):
    with open("tello_foto.jpg", "wb") as f:              # take_picture() sonrası gelen JPEG
        f.write(data)


def baglanti(event, sender, data=None, recv_time=None, **args):
    sakla("baglanti", event is sender.EVENT_CONNECTED, time.monotonic())


# ---------------------------------------------------------------------------
# 4) Görüntü (tick YOK; karede zaman bilgisi yok)
# ---------------------------------------------------------------------------
def video_paketi(event, sender, data, recv_time, **args):
    # Ham H.264 parçası (UDP paketi, 2 byte başlık çıkarılmış). Sadece paket sayıyoruz.
    with kilit:
        sayi, _ = son.get("video_paketi", (0, None))
        son["video_paketi"] = (sayi + 1, recv_time)


def goruntu_oku(drone, calisiyor):
    import av

    kap = av.open(drone.get_video_stream())
    for kare in kap.decode(video=0):
        if not calisiyor.is_set():
            break
        goruntu = kare.to_ndarray(format="bgr24")       # 720x960x3 numpy (OpenCV için BGR)
        # Karenin drone zamanı yok; ancak çözüldüğü anı kaydedebiliriz.
        sakla("goruntu", goruntu, time.monotonic())


# ---------------------------------------------------------------------------
# 5) Zaman düzeltmesi (isteğe bağlı, §2.2): tick -> bilgisayar saati
# ---------------------------------------------------------------------------
class MvoContainer(Container):
    """Kütüphanede MVO için hazır Container yok; böyle tanımlanır."""
    SAMPLE = tellopy.LogNewMvoFeedback
    EVENTS = (tellopy.Tello.EVENT_SAMPLE_MVO,)


def zaman_duzeltme_kur(drone):
    imular = ImuContainer(drone)                 # saat sadece IMU'dan beslenir (kütüphanenin tercihi)
    gyrolar = GyroContainer(drone)
    mvolar = MvoContainer(drone)
    saat = TickClock(imular)
    duzeltilmis = {
        "imu": Retimer(imular, saat),
        "gyro": Retimer(gyrolar, saat),
        "mvo": Retimer(mvolar, saat),
    }
    for ad, retimer in duzeltilmis.items():
        # Her kayıt bir kopya olarak tekrar yayınlanır: event_time = tick'ten bulunan zaman.
        # event_time_std None ise düzeltilemedi (saat henüz hazır değil), event_time = recv_time kalır.
        retimer.subscribe(lambda kayit, ad=ad: sakla(
            f"{ad}_zaman", {"recv_time": kayit.recv_time, "event_time": kayit.event_time,
                            "std_s": kayit.event_time_std}, kayit.recv_time))
    return saat, duzeltilmis      # referansları tutun, yoksa çöp toplayıcı silebilir


# ---------------------------------------------------------------------------
# 6) Hepsini bağla
# ---------------------------------------------------------------------------
def abone_ol(drone):
    d = drone
    for olay, fonksiyon in [
        (d.EVENT_FLIGHT_DATA, ucus_verisi),
        (d.EVENT_SAMPLE_IMU, imu), (d.EVENT_SAMPLE_MVO, mvo), (d.EVENT_SAMPLE_GYRO, gyro),
        (d.EVENT_SAMPLE_TOF, tof), (d.EVENT_SAMPLE_CONTROL, kontrol), (d.EVENT_SAMPLE_RAW, diger_kayitlar),
        (d.EVENT_WIFI, wifi), (d.EVENT_LIGHT, isik), (d.EVENT_LOG_HEADER, gunluk_basligi),
        (d.EVENT_SAMPLE_COMMAND_ACK, komut_yaniti), (d.EVENT_SAMPLE_COMMAND_TIMEOUT, komut_yanitsiz),
        (d.EVENT_CALIBRATION_STATUS, kalibrasyon), (d.EVENT_FILE_RECEIVED, dosya),
        (d.EVENT_CONNECTED, baglanti), (d.EVENT_DISCONNECTED, baglanti),
        (d.EVENT_VIDEO_FRAME, video_paketi),
    ]:
        d.subscribe(olay, fonksiyon)


def main():
    drone = tellopy.Tello()
    drone.set_loglevel(drone.LOG_WARN)
    calisiyor = threading.Event()
    calisiyor.set()
    try:
        abone_ol(drone)                               # connect'ten önce: ilk paketler kaçmasın
        saat, duzeltilmis = zaman_duzeltme_kur(drone)
        drone.connect()
        drone.wait_for_connection(30.0)
        threading.Thread(target=goruntu_oku, args=(drone, calisiyor), daemon=True).start()
        while True:
            time.sleep(1.0)
            with kilit:
                kopya = dict(son)
            simdi = time.monotonic()
            print("-" * 60)
            for ad, (deger, recv_time) in sorted(kopya.items()):
                if ad == "goruntu":
                    deger = f"kare {deger.shape}"
                yas = "" if recv_time is None else f"({simdi - recv_time:.2f} s once)"
                print(f"{ad:16} {yas:14} {deger}")
    except KeyboardInterrupt:
        pass
    finally:
        calisiyor.clear()
        drone.quit()          # TelloPy thread'leri daemon değil: çağrılmazsa program kapanmaz


if __name__ == "__main__":
    main()
```

Bu örnek, TelloPy'nin kendi sahte drone'u (`tests/support/fake_drone.py`) ile bir kez çalıştırıldı:
- Uçuş verisi, Wi-Fi, ışık, IMU, MVO, ToF ve tanımsız kayıt olaylarının hepsi geldi.
- `fly_time = 300` ve pil 3800 doğru okundu (§9.1 düzeltmesi).

Gerçek drone'da kontrol edilecekler: Görüntü, komut yanıtları ve zaman düzeltmesi. Zaman düzeltmesinin devreye girmesi için ~30 IMU kaydı, yani birkaç saniye gerekir.
