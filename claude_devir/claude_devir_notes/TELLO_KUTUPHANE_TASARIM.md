# Yeni Tello kütüphanesi: tasarım notu

TelloPy'nin yerine yazılacak, en alt seviye ve en sade arayüz: drone'a bağlanır, komut gönderir, drone'un gönderdiği verileri okuma fonksiyonlarıyla verir. Başka hiçbir şey yapmaz.

Kullanıcı kendi Python kodundan çağırır. Odometri, filtreleme, zaman düzeltmesi, ROS, sürü yönetimi bu kütüphanede **yok**; hepsi üst katmanın işi.

## 1. Kaynaklar (yazan bunları okuyacak)

| Kaynak | Ne için |
|---|---|
| `TELLO_VERI_RAPORU.md` | Her verinin byte konumu, tipi, birimi, sıklığı. Alan anlamlarında **rapor esastır**; TelloPy'deki bazı adlar yanlış (§3) |
| `TelloPy/tellopy/_internal/tello.py` | Bağlantı kurulumu, paket gönderme zamanlaması, video isteği, günlük onayı. Davranış buradan aynen alınır |
| `TelloPy/tellopy/_internal/protocol.py` | Paket ve kayıt çözme, CRC |
| `kayitlar/paket_dinleme_20261111_105319/`, `…_143727/` | İki gerçek uçuşun ham paketleri (`paketler.jsonl`); testlerin verisi |

## 2. Kullanım

```python
from tellolink import Tello

drone = Tello()                  # tek drone
# drone = Tello(local_ip="192.168.10.2")   # birden çok drone: bu drone'un ağına bağlı adaptörün adresi
drone.connect()

imu = drone.read_imu()           # son IMU kaydı; henüz gelmediyse None
print(imu.acc_x, imu.gyro_z, imu.tick, imu.recv_time)

kare = drone.read_frame()        # son video karesi, çözülmüş
kare.image                       # numpy dizisi (yükseklik × genişlik × 3, BGR)

drone.takeoff()
drone.set_sticks(pitch=0.3, roll=0, yaw=0, throttle=0)
drone.land()
drone.close()
```

Geri çağrı (callback), olay aboneliği, ayrı kurulması gereken katman yok. Kütüphane arka planda paketleri alır; kullanıcı istediği anda okur.

## 3. Fonksiyonlar

### Bağlantı ve komutlar

| Fonksiyon | Ne yapar |
|---|---|
| `Tello(local_ip=None)` | `local_ip` verilirse soketler o adaptöre bağlanır (üç drone = üç adaptör, üç nesne). Tek parametre bu |
| `connect(timeout=10)`, `close()`, `connected` | Bağlantı. Video `connect` ile birlikte başlar |
| `takeoff()`, `land()`, `emergency()` | Kalkış, iniş, motorları hemen durdurma |
| `set_sticks(pitch, roll, yaw, throttle)` | −1…1. Yeni değer verilene kadar son değer gönderilmeye devam eder |
| `set_altitude_limit(m)`, `set_low_battery_threshold(percent)` | Yükseklik sınırı, düşük pil eşiği |
| `set_wifi_name(name)`, `set_wifi_password(password)` | Drone'un Wi-Fi adı ve şifresi (drone yeniden başlar) |

### Veri okuma

Her veri için iki fonksiyon:
- `read_x()` → **son** kayıt (hiç gelmediyse `None`).
- `read_x_new()` → son çağrıdan beri gelen **bütün** kayıtların listesi (hiçbiri kaçmasın isteniyorsa; odometri için bu kullanılır).

| Fonksiyon | Veri | Sıklık |
|---|---|---|
| `read_status()` | Uçuş durumu: yükseklik, ileri/sağa/aşağı hız, pil yüzdesi, pil gerilimi, uçuş modu, bayraklar | 10 Hz |
| `read_imu()` | İvme, açısal hız, kuaterniyon, hız, barometre, sıcaklık | 10 Hz |
| `read_gyro()` | Jiroskop kaydı (LogGyro) | 20 Hz, havada |
| `read_mvo()` | Optik akış hızı, konumu, yüksekliği, geçerlilik bitleri | 5 Hz |
| `read_tof()` | Mesafe sensörü | 5 Hz |
| `read_nav()` | Kayıt 2064: hız, kalkışta sıçramayan konum, yükseklik | 10 Hz |
| `read_osd()` | Kayıt 12: açılar, hız, yaw hızı, uçuş süresi | 1.7 Hz |
| `read_sticks()` | Kayıt 1000: drone'un gördüğü çubuklar | 5 Hz |
| `read_attitude_target()` | Kayıt 1304: hedef ve gerçek yönelim | 2.5 Hz |
| `read_motors()` | Kayıt 1307: dört motorun PWM yüzdesi | 10 Hz, havada |
| `read_battery()` | Kayıt 1710: pil gerilimi | 5 Hz |
| `read_wifi()` | Wi-Fi sinyal gücü | ~ |
| `read_frame()` | Son video karesi, **çözülmüş**: `image` (numpy, BGR), `data` (karenin ham H.264 baytları), `keyframe`; `read_frame_new()` hepsini verir | 30 Hz |
| `read_raw(record_id)` | Çözülmeyen bir kaydın ham byte'ları | — |

Her kayıt basit bir nesne (dataclass). Ortak alanlar:
- `recv_time`: paketin bilgisayara vardığı an (`time.monotonic()`).
- `tick`: drone'un sayacı (günlük kayıtlarında var; uçuş durumu, Wi-Fi ve video karesinde `None`).

Görüntü kütüphanenin içinde çözülür (TelloPy'de kullanıcı `av.open(drone.get_video_stream())` ile çözüyordu):
- Bir arka plan thread'i kareleri PyAV (`av`) ile çözer.
- Kareler çözücüye **tek tek** verilir (akış olarak değil); böylece her kare, baytlarının bilgisayara vardığı anı `recv_time` olarak taşır.
- Çözülemeyen kare (ör. ilk anahtar kareden öncekiler) atlanır, hata verilmez.
- SPS/PPS isteğinin tekrarı gibi video davranışları TelloPy'deki gibi kalır.

Zaman düzeltmesi yapılmaz; `tick` ve `recv_time` ham olarak verilir, düzeltmek isteyen üst katmanda yapar.

Birimler ve eksenler raporda yazdığı gibi, çevirme yok: drone ne gönderiyorsa o (yalnızca ölçek uygulanır: mm → m, dm/s → m/s, mV → V). Eksenler x ileri, y sağa, z aşağı.

## 4. Çıkarılanlar

Olay/abonelik sistemi, zaman düzeltmesi (`estimator.py`), Container sınıfları, kayıt/oynatma araçları, flip, avuçtan kalkış, fotoğraf, kalibrasyon, pozlama ve video ayarları, yatma açısı sınırı, örnek programlar, sahte drone test altyapısı.

## 5. Doğrulama

1. **Kayıtlardan:** İki uçuşun `paketler.jsonl` dosyası yeni çözücüden geçirilir; her alan TelloPy'nin aynı paketten çözdüğü değerle karşılaştırılır. CRC hatası 0 olmalı.
2. **Gerçek drone:** bağlantı, video, kalkış/iniş, çubuklar. Kullanıcı yapar.
3. **Üç adaptör:** `local_ip` ile üç drone'a aynı anda bağlanma ayrıca denenir (Linux'ta adrese bağlanmak yetmezse adaptöre bağlama eklenir).

## 6. Yerleşim

Proje kökünde `tellolink/`: `protocol.py` (paket ve kayıt çözme), `tello.py` (soketler, alım thread'i, komutlar, okuma fonksiyonları), `README.md`. Bağımlılık: yalnızca görüntü için `av` ve `numpy`; geri kalanı standart kütüphane.
TelloPy'ye dokunulmaz.
