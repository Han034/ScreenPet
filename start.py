import pygame
import sys
import math
import random
import json
import os
from collections import deque
import shutil # Dosya kopyalamak için
# Tkinter importları (Dosya seçimi için)
try:
    import tkinter as tk
    from tkinter import filedialog
    tkinter_available = True
except ImportError:
    tkinter_available = False
    print("Uyarı: tkinter modülü bulunamadı. Dosya seçme özelliği çalışmayacak.")


# --- Platforma Özel Kütüphaneleri Yüklemeyi Dene (Windows için) ---
IS_WINDOWS = (sys.platform == 'win32')
hwnd = None
try:
    if IS_WINDOWS:
        import win32gui
        import win32con
        import win32api # RGB fonksiyonu için gerekli
        print("pywin32 kütüphanesi bulundu.")
    else:
        print("Windows dışı platform, şeffaflık/en üstte kalma için özel kod çalıştırılmayacak.")
except ImportError:
    print("Uyarı: pywin32 kütüphanesi bulunamadı. Gerçek şeffaflık ve en üstte kalma özellikleri Windows'ta çalışmayacak.")
    IS_WINDOWS = False

# --- Ayar ve Dil Dosyası Adları ---
SETTINGS_FILE = "ayarlar.json"
LANGUAGE_FILE = "languages.json"

# --- Varsayılan Ayarlar ---
DEFAULT_SETTINGS = {
    "hayvan_ismi": "Maviş",
    "hayvan_yas": 1,
    "hayvan_color": [0, 0, 255], # Yedek renk
    "ev_color": [0, 255, 0],     # Yedek renk
    "top_color": [255, 0, 0],    # Top rengi (Yedek veya görsel yoksa)
    "language": "tr",
    "start_with_windows": False,
    "show_object_names": True
}

# --- Dil ve Ayar Fonksiyonları ---
LANGUAGES = {}
def load_languages():
    global LANGUAGES
    lang_file_path = os.path.join(os.path.dirname(__file__), LANGUAGE_FILE) if '__file__' in locals() else LANGUAGE_FILE
    if os.path.exists(lang_file_path):
        try:
            with open(lang_file_path, 'r', encoding='utf-8') as f: LANGUAGES = json.load(f)
            print("Dil dosyası yüklendi.")
        except (json.JSONDecodeError, IOError) as e: print(f"Dil dosyası okunamadı ({e})"); LANGUAGES = {"tr": {"error": "..."}, "en": {"error": "..."}}
    else: print(f"'{lang_file_path}' bulunamadı."); LANGUAGES = {"tr": {"error": "..."}, "en": {"error": "..."}}

def get_text(key, lang):
    default_lang = DEFAULT_SETTINGS["language"]
    lang_dict = LANGUAGES.get(lang, LANGUAGES.get(default_lang, {}))
    return lang_dict.get(key, f"<{key}>")

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), SETTINGS_FILE) if '__file__' in locals() else SETTINGS_FILE
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f: settings = json.load(f)
            for key, value in DEFAULT_SETTINGS.items(): settings.setdefault(key, value)
            settings["hayvan_color"] = tuple(settings["hayvan_color"]); settings["ev_color"] = tuple(settings["ev_color"]); settings["top_color"] = tuple(settings["top_color"])
            print(f"Ayarlar yüklendi: {settings}"); return settings
        except (json.JSONDecodeError, IOError, TypeError, KeyError) as e:
            print(f"Ayarlar dosyası okunamadı ({e}), varsayılanlar kullanılıyor.")
            defaults = DEFAULT_SETTINGS.copy(); defaults["hayvan_color"] = tuple(defaults["hayvan_color"]); defaults["ev_color"] = tuple(defaults["ev_color"]); defaults["top_color"] = tuple(defaults["top_color"]); return defaults
    else:
        print("Ayar dosyası bulunamadı, varsayılanlar kullanılıyor.")
        defaults = DEFAULT_SETTINGS.copy(); defaults["hayvan_color"] = tuple(defaults["hayvan_color"]); defaults["ev_color"] = tuple(defaults["ev_color"]); defaults["top_color"] = tuple(defaults["top_color"]); return defaults

def save_settings(settings):
    settings_path = os.path.join(os.path.dirname(__file__), SETTINGS_FILE) if '__file__' in locals() else SETTINGS_FILE
    try:
        save_data = settings.copy(); save_data["hayvan_color"] = list(settings["hayvan_color"]); save_data["ev_color"] = list(settings["ev_color"]); save_data["top_color"] = list(settings["top_color"])
        with open(settings_path, 'w') as f: json.dump(save_data, f, indent=4)
        lang = settings.get("language", "tr"); print(get_text("settings_saved", lang), settings)
    except IOError as e: lang = settings.get("language", "tr"); print(get_text("settings_save_error", lang).format(e=e))
    except TypeError as e: lang = settings.get("language", "tr"); print(get_text("settings_save_type_error", lang).format(e=e))

def restart_application():
    try:
        print("Uygulama yeniden başlatılıyor..."); save_settings(current_settings)
        python_executable = sys.executable; script_path = os.path.abspath(__file__) if '__file__' in locals() else sys.argv[0]
        os.execl(python_executable, python_executable, script_path, *sys.argv[1:])
    except Exception as e: lang = current_settings.get("language", "tr"); print(get_text("restart_failed", lang).format(e=e))


# --- Yardımcı Fonksiyonlar ---
def create_asset_folders():
    base_path = os.path.dirname(__file__) if "__file__" in locals() else os.getcwd()
    assets_folder = os.path.join(base_path, "Assets")
    subfolders = ["Animal", "House", "Ball"]
    schema_folder_name = "UserSchema"
    default_folder_name = "Default"
    try:
        os.makedirs(assets_folder, exist_ok=True)
        for sub in subfolders:
            os.makedirs(os.path.join(assets_folder, sub, schema_folder_name), exist_ok=True)
            os.makedirs(os.path.join(assets_folder, sub, default_folder_name), exist_ok=True)
        print("Assets klasör yapısı kontrol edildi/oluşturuldu.")
    except OSError as e: print(f"Assets klasörleri oluşturulurken hata: {e}")

def load_image(asset_type, default_filename, user_filename="user_default.png", size=None):
    base_path = os.path.dirname(__file__) if "__file__" in locals() else os.getcwd()
    user_folder = os.path.join(base_path, "Assets", asset_type, "UserSchema")
    default_folder = os.path.join(base_path, "Assets", asset_type, "Default")
    user_path = os.path.join(user_folder, user_filename)
    default_path = os.path.join(default_folder, default_filename)
    image = None
    final_path_loaded = None
    try:
        if os.path.exists(user_path):
            image = pygame.image.load(user_path).convert_alpha()
            final_path_loaded = user_path
        elif os.path.exists(default_path):
             image = pygame.image.load(default_path).convert_alpha()
             final_path_loaded = default_path
        if image:
            if size:
                try: image = pygame.transform.scale(image, size)
                except ValueError:
                     print(f"Uyarı: Görsel ölçeklenemedi '{final_path_loaded}'. Orijinal boyut kullanılacak.")
                     if final_path_loaded:
                         try: image = pygame.image.load(final_path_loaded).convert_alpha()
                         except pygame.error as e: print(f"Orijinal görsel bile yüklenemedi: {e}"); image = None
        return image
    except pygame.error as e: print(f"Uyarı: Görsel yüklenemedi '{default_filename}' veya '{user_filename}' ({e})."); return None
    except Exception as e: print(f"Görsel yüklenirken beklenmedik hata: {e}"); return None

def open_file_dialog(title="Dosya Seç", filetypes=(("PNG files", "*.png"), ("All files", "*.*"))):
    if not tkinter_available: print("Hata: tkinter modülü yüklenemediği için dosya seçilemiyor."); return None
    try:
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        if filepath: print(f"Dosya seçildi: {filepath}"); return filepath
        else: print("Dosya seçimi iptal edildi."); return None
    except Exception as e: print(f"Dosya seçme penceresi açılırken hata: {e}"); return None

# --- Gerekli Klasörleri Oluştur ---
create_asset_folders()

# --- Pygame Başlatma, Dil ve Ayarları Yükleme ---
pygame.init()
load_languages()
current_settings = load_settings()
current_language = current_settings.get("language", "tr")

# --- Renkler ---
WHITE = (255, 255, 255); BLACK = (0, 0, 0); BLUE = (0, 0, 255); YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128); GREEN = (0, 255, 0); ORANGE = (255, 165, 0); BROWN = (139, 69, 19)
RED = (255, 0, 0); PINK = (255, 192, 203); GRAY = (200, 200, 200); LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (80, 80, 80); SETTINGS_BG_COLOR = (60, 60, 60); SETTINGS_TAB_BG = (40, 40, 40)
SETTINGS_TAB_ACTIVE_BG = (70, 70, 70); SETTINGS_TEXT_COLOR = (230, 230, 230)
TEXT_COLOR = (50, 50, 50); INPUT_ACTIVE_BORDER = (255, 255, 255); PARTICLE_BLUE = (100, 100, 255)
TRANSPARENT_COLOR = BLACK; BACKGROUND_COLOR = TRANSPARENT_COLOR

# --- Ekran Ayarları ---
screen = None
try:
    display_info = pygame.display.Info()
    SCREEN_WIDTH = display_info.current_w; SCREEN_HEIGHT = display_info.current_h
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
    print(f"Çerçevesiz tam ekran modu: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    if IS_WINDOWS:
        try:
            hwnd = pygame.display.get_wm_info()['window']
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
            print("Windows: Katmanlı pencere stili ayarlandı.")
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENT_COLOR), 0, win32con.LWA_COLORKEY)
            print(f"Windows: Renk anahtarı ({TRANSPARENT_COLOR}) ile şeffaflık ayarlandı.")
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            print("Windows: Pencere en üste ayarlandı.")
        except Exception as e: print(f"Windows API çağrısı başarısız oldu: {e}"); IS_WINDOWS = False; BACKGROUND_COLOR = LIGHT_GRAY
except pygame.error as e:
    print(f"Tam ekran/çerçevesiz mod ayarlanamadı ({e}), varsayılan pencere.")
    SCREEN_WIDTH = 800; SCREEN_HEIGHT = 600
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    BACKGROUND_COLOR = WHITE
if screen is None: print("Hata: Pygame ekranı başlatılamadı."); sys.exit()

# Fontlar
try:
    font = pygame.font.Font(None, 24); menu_font = pygame.font.Font(None, 22)
    settings_font = pygame.font.Font(None, 26); settings_label_font = pygame.font.Font(None, 28)
    settings_tab_font = pygame.font.Font(None, 24)
    asset_label_font = pygame.font.Font(None, 18)
except: # Alternatifler
    font = pygame.font.SysFont('arial', 20); menu_font = pygame.font.SysFont('arial', 18)
    settings_font = pygame.font.SysFont('arial', 20); settings_label_font = pygame.font.SysFont('arial', 22)
    settings_tab_font = pygame.font.SysFont('arial', 18)
    asset_label_font = pygame.font.SysFont('arial', 14)


# --- Parçacık (Particle) Sınıfı ---
class Particle:
    def __init__(self, x, y, color=None): self.x=x; self.y=y; angle=random.uniform(0, 2*math.pi); speed=random.uniform(1,4); self.vx=math.cos(angle)*speed; self.vy=math.sin(angle)*speed; self.size=random.randint(4,8); self.color = color if color else random.choice([RED, PINK]); self.lifespan=random.randint(30,50)
    def update(self): self.x+=self.vx; self.y+=self.vy; self.lifespan-=1; self.size=max(0,self.size-0.1)
    def draw(self, s): pygame.draw.circle(s,self.color,(int(self.x),int(self.y)),int(self.size)) if self.lifespan>0 and self.size>0 else None
particles = []
def create_particles(pos, count, color=None): [particles.append(Particle(pos[0],pos[1], color=color)) for _ in range(count)]

# --- Nesne Tanımları ---
hayvan_ismi = current_settings["hayvan_ismi"]
hayvan_yas = current_settings["hayvan_yas"]
hayvan_color = current_settings["hayvan_color"]
ev_color = current_settings["ev_color"]
top_color = current_settings["top_color"]
hayvan_rect = pygame.Rect(100, SCREEN_HEIGHT - 100, 64, 64)
hayvan_mutluluk = 100; hayvan_aclik = 100; hayvan_uyku = 100
MUTLULUK_DECAY_RATE = 0.05; ACLIK_DECAY_RATE = 0.1
hedef_konum = None; is_chasing_ball = False
ev_rect = pygame.Rect(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200, 150, 150)
top_yaricap = 15; top_merkez = [SCREEN_WIDTH // 2, 100]
top_hiz_x = 0; top_hiz_y = 0; top_angle = 0.0; TOP_ROTATION_FACTOR = 60
yercekimi = 0.5; sekme_faktoru = -0.7; yatay_sekme_faktoru = -0.9
top_drag_rect = pygame.Rect(top_merkez[0]-top_yaricap, top_merkez[1]-top_yaricap, top_yaricap*2, top_yaricap*2)
top_ekranda = False

# --- Görselleri Yükleme ---
hayvan_boyut = hayvan_rect.size; animal_folder = "Animal"
img_idle = load_image(animal_folder, "Cat.png", user_filename="user_cat.png", size=hayvan_boyut)
if img_idle is None: print("Kritik Hata: Ana hayvan görseli yüklenemedi!"); pygame.quit(); sys.exit()
img_sit_left = load_image(animal_folder, "left_sit_cat.png", user_filename="user_sit_left.png", size=hayvan_boyut)
img_sit_right = load_image(animal_folder, "right_sit_cat.png", user_filename="user_sit_right.png", size=hayvan_boyut)
img_back = load_image(animal_folder, "back_cat.png", user_filename="user_back.png", size=hayvan_boyut)
img_sleep = load_image(animal_folder, "right_sleep_cat.png", user_filename="user_sleep.png", size=hayvan_boyut)
img_trigger_left = load_image(animal_folder, "left_trigger_cat.png", user_filename="user_trigger_left.png", size=hayvan_boyut)
img_trigger_right = load_image(animal_folder, "right_trigger_cat.png", user_filename="user_trigger_right.png", size=hayvan_boyut)
img_sad = load_image(animal_folder, "sad_cat.png", user_filename="user_sad.png", size=hayvan_boyut)
img_angry = load_image(animal_folder, "angry_cat.png", user_filename="user_angry.png", size=hayvan_boyut)
img_happy = load_image(animal_folder, "happy_cat.png", user_filename="user_happy.png", size=hayvan_boyut)
img_smile = load_image(animal_folder, "smile_cat.png", user_filename="user_smile.png", size=hayvan_boyut)
img_kips = load_image(animal_folder, "kips_cat.png", user_filename="user_kips.png", size=hayvan_boyut)
img_smile_2 = load_image(animal_folder, "smile_cat_2.png", user_filename="user_smile2.png", size=hayvan_boyut)
img_walk_frames = []
img_walk_frames_data = []
for i in range(2, 7):
    default_name = f"cat_walk_{i}.png"; user_name = f"user_walk_{i}.png"
    frame = load_image(animal_folder, default_name, user_filename=user_name, size=hayvan_boyut)
    if frame: img_walk_frames.append(frame); img_walk_frames_data.append(("pet_walk_" + str(i), animal_folder, default_name, user_name, hayvan_boyut, f"img_walk_frames[{len(img_walk_frames)-1}]"))
if not img_walk_frames: print("Uyarı: Hiç yürüme animasyon karesi yüklenemedi!")
ev_boyut = ev_rect.size; house_folder = "House"
ev_image_scaled = load_image(house_folder, "house.png", user_filename="user_house.png", size=ev_boyut)
ball_folder = "Ball"; top_boyut = (top_yaricap * 2, top_yaricap * 2)
img_ball = load_image(ball_folder, "ball.png", user_filename="user_ball.png", size=top_boyut)

# --- Değiştirilebilir Varlıkları Tanımla ---
asset_list = [
    ("pet_idle", "Animal", "Cat.png", "user_cat.png", hayvan_boyut, "img_idle"),
    ("house", "House", "house.png", "user_house.png", ev_boyut, "ev_image_scaled"),
    ("ball", "Ball", "ball.png", "user_ball.png", top_boyut, "img_ball"),
    ("pet_sit_left", "Animal", "left_sit_cat.png", "user_sit_left.png", hayvan_boyut, "img_sit_left"),
    ("pet_sit_right", "Animal", "right_sit_cat.png", "user_sit_right.png", hayvan_boyut, "img_sit_right"),
    ("pet_back", "Animal", "back_cat.png", "user_back.png", hayvan_boyut, "img_back"),
    ("pet_sleep", "Animal", "right_sleep_cat.png", "user_sleep.png", hayvan_boyut, "img_sleep"),
    ("pet_trigger_left", "Animal", "left_trigger_cat.png", "user_trigger_left.png", hayvan_boyut, "img_trigger_left"),
    ("pet_trigger_right", "Animal", "right_trigger_cat.png", "user_trigger_right.png", hayvan_boyut, "img_trigger_right"),
    ("pet_sad", "Animal", "sad_cat.png", "user_sad.png", hayvan_boyut, "img_sad"),
    ("pet_angry", "Animal", "angry_cat.png", "user_angry.png", hayvan_boyut, "img_angry"),
    ("pet_happy", "Animal", "happy_cat.png", "user_happy.png", hayvan_boyut, "img_happy"),
    ("pet_smile", "Animal", "smile_cat.png", "user_smile.png", hayvan_boyut, "img_smile"),
    ("pet_kips", "Animal", "kips_cat.png", "user_kips.png", hayvan_boyut, "img_kips"),
    ("pet_smile2", "Animal", "smile_cat_2.png", "user_smile2.png", hayvan_boyut, "img_smile_2"),
]
asset_list.extend(img_walk_frames_data)


# --- Durum Değişkenleri ---
# ... (Aynı) ...
hayvan_surukleniyor = False; top_surukleniyor = False; ev_surukleniyor = False
fare_offset_x = 0; fare_offset_y = 0; hareket_hizi = 3; hayvan_menu_aktif = False; ev_menu_aktif = False
ayarlar_menu_aktif = False; aktif_ayar_sekmesi = "pet"; menu_konumu = (0, 0); menu_genislik = 150
menu_yukseklik = 100; ev_menu_genislik = 120; ev_menu_yukseklik = 110
topu_getir_button_rect = None; ayarlar_button_rect = None; yemek_ver_button_rect = None
ayarlar_kapat_button_rect = None; hayvan_isim_duzenle_button_rect = None; hayvan_isim_input_rect = None
hayvan_renk_butonlari = {}; ev_renk_butonlari = {}; top_renk_butonlari = {}
ayarlar_sifirla_button_rect = None; ayarlar_yeniden_baslat_button_rect = None; ayarlar_dil_tr_button_rect = None
ayarlar_dil_en_button_rect = None; ayarlar_windows_baslat_button_rect = None; ayarlar_sekme_butonlari = {}
ayarlar_isim_goster_button_rect = None; assets_edit_buttons = {}
isim_duzenleme_aktif = False; aktif_metin_girisi = ""; cursor_blink_timer = 0; cursor_visible = True
son_ev_tiklama_zamani = 0; cift_tiklama_suresi = 500; hayvan_menu_rect_cache = None; ev_menu_rect_cache = None
assets_scroll_y = 0; assets_content_height = 0; assets_scrollbar_rect = None
assets_scrollbar_handle_rect = None; scrollbar_dragging = False; scrollbar_drag_offset_y = 0


# --- Hayvan Durumları ve Zamanlayıcılar ---
# ... (Aynı) ...
HAYVAN_STATE_IDLE = "idle"; HAYVAN_STATE_WALKING = "walking"; HAYVAN_STATE_SITTING_LEFT = "sitting_left"; HAYVAN_STATE_SITTING_RIGHT = "sitting_right"
HAYVAN_STATE_BACK = "back"; HAYVAN_STATE_TRIGGERED_LEFT = "triggered_left"; HAYVAN_STATE_TRIGGERED_RIGHT = "triggered_right"; HAYVAN_STATE_SLEEPING = "sleeping"
HAYVAN_STATE_GOING_HOME = "going_home"; HAYVAN_STATE_SAD = "sad"; HAYVAN_STATE_ANGRY = "angry"; HAYVAN_STATE_HAPPY = "happy"
HAYVAN_STATE_SMILE = "smile"; HAYVAN_STATE_KIPS = "kips"; HAYVAN_STATE_SMILE2 = "smile2"
hayvan_state = HAYVAN_STATE_IDLE; hayvan_direction = "right"; hayvan_idle_timer = 0; hayvan_state_timer = 0; hayvan_sleep_timer = 0
hayvan_anim_timer = 0; hayvan_anim_index = 0; HAYVAN_ANIM_SPEED = 100; IDLE_ACTION_THRESHOLD = 5000
SHORT_ACTION_DURATION = 1500; SIT_BACK_DURATION = 2500; SLEEP_THRESHOLD = 15000; TRIGGER_DURATION = 400; HAPPY_DURATION = 1000; ANGRY_DURATION = 3000
hayvan_click_times = deque(maxlen=4); MULTI_CLICK_INTERVAL = 600; MULTI_CLICK_COUNT = 3


# Oyun Döngüsü
running = True; clock = pygame.time.Clock()

# Ana oyun döngüsü
while running:
    # ... (Olay İşleme ve Oyun Mantığı kodları öncekiyle aynı) ...
    delta_time = clock.tick(60); current_time = pygame.time.get_ticks(); mouse_pos = pygame.mouse.get_pos(); events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT: running = False
        elif event.type == pygame.ACTIVEEVENT:
            if event.gain == 0 and event.state == 1:
                if hayvan_menu_aktif: hayvan_menu_aktif = False; hayvan_menu_rect_cache = None
                if ev_menu_aktif: ev_menu_aktif = False; ev_menu_rect_cache = None
        if ayarlar_menu_aktif:
            if event.type == pygame.MOUSEWHEEL and aktif_ayar_sekmesi == "assets":
                 if icerik_alani_rect.collidepoint(mouse_pos):
                     assets_scroll_y -= event.y * 30; view_height = icerik_alani_rect.height - 2 * icerik_padding; max_scroll = max(0, assets_content_height - view_height); assets_scroll_y = max(0, min(assets_scroll_y, max_scroll))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ayarlar_kapat_button_rect and ayarlar_kapat_button_rect.collidepoint(event.pos): ayarlar_menu_aktif = False; isim_duzenleme_aktif = False; continue
                if assets_scrollbar_handle_rect and assets_scrollbar_handle_rect.collidepoint(event.pos): scrollbar_dragging = True; scrollbar_drag_offset_y = event.pos[1] - assets_scrollbar_handle_rect.y; continue
                tab_clicked = False; sekmeler_keys = ["pet", "house", "ball", "assets", "game_settings"]
                for sekme_key, rect in ayarlar_sekme_butonlari.items():
                    if rect and rect.collidepoint(event.pos):
                        if aktif_ayar_sekmesi != sekme_key: aktif_ayar_sekmesi = sekme_key; isim_duzenleme_aktif = False; assets_scroll_y = 0
                        tab_clicked = True; break
                if tab_clicked: continue
                if isim_duzenleme_aktif and hayvan_isim_input_rect and not hayvan_isim_input_rect.collidepoint(event.pos): isim_duzenleme_aktif = False
                if aktif_ayar_sekmesi == "pet":
                    if hayvan_isim_duzenle_button_rect and hayvan_isim_duzenle_button_rect.collidepoint(event.pos): isim_duzenleme_aktif = True; aktif_metin_girisi = hayvan_ismi; cursor_blink_timer = current_time; cursor_visible = True
                    for renk, rect in hayvan_renk_butonlari.items():
                        if rect and rect.collidepoint(event.pos): print(f"Hayvan renk butonu tıklandı: {renk} (Görsel kullanılıyor)"); break
                elif aktif_ayar_sekmesi == "house":
                    for renk, rect in ev_renk_butonlari.items():
                        if rect and rect.collidepoint(event.pos): ev_color = renk; current_settings["ev_color"] = renk; save_settings(current_settings); break
                elif aktif_ayar_sekmesi == "ball":
                    for renk, rect in top_renk_butonlari.items():
                        if rect and rect.collidepoint(event.pos): top_color = renk; current_settings["top_color"] = renk; save_settings(current_settings); break
                elif aktif_ayar_sekmesi == "assets":
                    clicked_on_asset_button = False
                    for asset_key, edit_button_rect in assets_edit_buttons.items():
                        if edit_button_rect and edit_button_rect.collidepoint(event.pos):
                            clicked_on_asset_button = True; asset_info = next((item for item in asset_list if item[5] == asset_key or item[0] == asset_key), None)
                            if asset_info:
                                display_key, asset_type, default_filename, user_filename, size, global_var_name = asset_info; target_folder = os.path.join("Assets", asset_type, "UserSchema")
                                if tkinter_available:
                                    selected_file = open_file_dialog(title=f"{get_text(display_key, current_language)} Görseli Seç", filetypes=(("PNG files", "*.png"),))
                                    if selected_file:
                                        try:
                                            base_path = os.path.dirname(__file__) if "__file__" in locals() else os.getcwd(); target_dir_path = os.path.join(base_path, target_folder); os.makedirs(target_dir_path, exist_ok=True); target_path = os.path.join(target_dir_path, user_filename); shutil.copy(selected_file, target_path); print(f"Dosya başarıyla '{target_path}' konumuna kopyalandı.")
                                            if global_var_name:
                                                new_image = load_image(asset_type, default_filename, user_filename=user_filename, size=size)
                                                if global_var_name.startswith("img_walk_frames"):
                                                    try:
                                                        index_str = global_var_name.split('[')[1].split(']')[0]; index = int(index_str)
                                                        if 0 <= index < len(img_walk_frames): img_walk_frames[index] = new_image; print(f"{global_var_name} görseli güncellendi.")
                                                        else: print(f"Uyarı: Geçersiz yürüme karesi indeksi: {index}")
                                                    except (IndexError, ValueError) as e: print(f"Yürüme karesi indeksi alınırken hata: {e}")
                                                elif global_var_name in globals(): globals()[global_var_name] = new_image; print(f"{global_var_name} görseli güncellendi.")
                                                else: print(f"Uyarı: Global değişken bulunamadı: {global_var_name}")
                                        except Exception as e: print(f"Dosya kopyalanırken veya yüklenirken hata: {e}")
                                else: print(f"\n--- Görsel Değiştirme Talimatı ({get_text(display_key, current_language)}) ---\ntkinter modülü bulunamadı.\n1. PNG dosyasını bulun.\n2. Dosyayı '{target_folder}' klasörüne kopyalayın.\n3. Adını '{user_filename}' yapın.\n4. Uygulamayı yeniden başlatın.")
                            break
                    if not clicked_on_asset_button and assets_scrollbar_rect and assets_scrollbar_rect.collidepoint(event.pos): pass
                elif aktif_ayar_sekmesi == "game_settings":
                    if ayarlar_sifirla_button_rect and ayarlar_sifirla_button_rect.collidepoint(event.pos): #... (sıfırlama)
                        current_settings = DEFAULT_SETTINGS.copy(); current_settings["hayvan_color"] = tuple(current_settings["hayvan_color"]); current_settings["ev_color"] = tuple(current_settings["ev_color"]); current_settings["top_color"] = tuple(current_settings["top_color"]); hayvan_ismi = current_settings["hayvan_ismi"]; hayvan_yas = current_settings["hayvan_yas"]; hayvan_color = current_settings["hayvan_color"]; ev_color = current_settings["ev_color"]; top_color = current_settings["top_color"]; current_language = current_settings["language"]; save_settings(current_settings); print(get_text("settings_reset", current_language)); pygame.display.set_caption(get_text("app_title", current_language))
                    elif ayarlar_yeniden_baslat_button_rect and ayarlar_yeniden_baslat_button_rect.collidepoint(event.pos): restart_application()
                    elif ayarlar_windows_baslat_button_rect and ayarlar_windows_baslat_button_rect.collidepoint(event.pos): #... (toggle)
                        current_settings["start_with_windows"] = not current_settings["start_with_windows"]; save_settings(current_settings); status_key = "start_win_enable_info" if current_settings["start_with_windows"] else "start_win_disable_info"; print(get_text(status_key, current_language), get_text("start_win_actual_impl_note", current_language))
                    elif ayarlar_isim_goster_button_rect and ayarlar_isim_goster_button_rect.collidepoint(event.pos): # İsim Göster/Gizle
                        current_settings["show_object_names"] = not current_settings["show_object_names"]; save_settings(current_settings)
                    elif ayarlar_dil_tr_button_rect and ayarlar_dil_tr_button_rect.collidepoint(event.pos): #... (dil tr)
                        print("TR button clicked");
                        if current_language != "tr": print(f"Changing language from {current_language} to tr"); current_settings["language"] = "tr"; current_language = "tr"; save_settings(current_settings); pygame.display.set_caption(get_text("app_title", current_language))
                    elif ayarlar_dil_en_button_rect and ayarlar_dil_en_button_rect.collidepoint(event.pos): #... (dil en)
                         print("EN button clicked");
                         if current_language != "en": print(f"Changing language from {current_language} to en"); current_settings["language"] = "en"; current_language = "en"; save_settings(current_settings); pygame.display.set_caption(get_text("app_title", current_language))
            elif isim_duzenleme_aktif and event.type == pygame.KEYDOWN: #... (isim düzenleme)
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER: hayvan_ismi = aktif_metin_girisi; current_settings["hayvan_ismi"] = hayvan_ismi; save_settings(current_settings); isim_duzenleme_aktif = False; print(get_text("name_updated", current_language).format(name=hayvan_ismi))
                elif event.key == pygame.K_BACKSPACE: aktif_metin_girisi = aktif_metin_girisi[:-1]
                elif event.key == pygame.K_ESCAPE: isim_duzenleme_aktif = False; print(get_text("name_edit_cancelled", current_language))
                else:
                    if len(aktif_metin_girisi) < 20 and event.unicode.isprintable(): aktif_metin_girisi += event.unicode
                cursor_visible = True; cursor_blink_timer = current_time
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False
            elif event.type == pygame.MOUSEMOTION and scrollbar_dragging:
                if assets_scrollbar_rect:
                    mouse_y = event.pos[1]; new_handle_y = mouse_y - scrollbar_drag_offset_y; new_handle_y = max(assets_scrollbar_rect.y, min(new_handle_y, assets_scrollbar_rect.bottom - assets_scrollbar_handle_rect.height))
                    view_height = icerik_alani_rect.height - 2 * icerik_padding; max_scroll = max(0, assets_content_height - view_height); scrollable_track_height = assets_scrollbar_rect.height - assets_scrollbar_handle_rect.height
                    if scrollable_track_height > 0: scroll_ratio = (new_handle_y - assets_scrollbar_rect.y) / scrollable_track_height; assets_scroll_y = scroll_ratio * max_scroll
                    else: assets_scroll_y = 0
                    assets_scroll_y = max(0, min(assets_scroll_y, max_scroll))
            continue
        if event.type == pygame.MOUSEBUTTONDOWN:
            menu_kapatildi = False
            if event.button == 1:
                if hayvan_menu_aktif:
                    if hayvan_menu_rect_cache and not hayvan_menu_rect_cache.collidepoint(event.pos): hayvan_menu_aktif = False; hayvan_menu_rect_cache = None; menu_kapatildi = True
                elif ev_menu_aktif:
                    is_on_button = False
                    if topu_getir_button_rect and topu_getir_button_rect.collidepoint(event.pos): is_on_button = True
                    if ayarlar_button_rect and ayarlar_button_rect.collidepoint(event.pos): is_on_button = True
                    if yemek_ver_button_rect and yemek_ver_button_rect.collidepoint(event.pos): is_on_button = True
                    if not is_on_button and ev_menu_rect_cache and not ev_menu_rect_cache.collidepoint(event.pos): ev_menu_aktif = False; ev_menu_rect_cache = None; menu_kapatildi = True
                if not menu_kapatildi:
                    if ev_menu_aktif:
                        if topu_getir_button_rect and topu_getir_button_rect.collidepoint(event.pos): top_ekranda = True; top_merkez = list(mouse_pos); top_hiz_y = 0; top_hiz_x = random.choice([-2, 2, -1.5, 1.5]); top_surukleniyor = True; fare_offset_x = 0; fare_offset_y = 0; top_drag_rect.center = top_merkez; ev_menu_aktif = False; is_chasing_ball = False; hayvan_state = HAYVAN_STATE_IDLE; ev_menu_rect_cache=None; top_angle = 0
                        elif ayarlar_button_rect and ayarlar_button_rect.collidepoint(event.pos): ayarlar_menu_aktif = True; ev_menu_aktif = False; aktif_ayar_sekmesi = "pet"; hayvan_state = HAYVAN_STATE_IDLE; ev_menu_rect_cache=None
                        elif yemek_ver_button_rect and yemek_ver_button_rect.collidepoint(event.pos): hayvan_aclik = 100; hayvan_mutluluk = min(100, hayvan_mutluluk + 10); hayvan_state = HAYVAN_STATE_HAPPY; hayvan_state_timer = HAPPY_DURATION; print("Hayvan beslendi!"); ev_menu_aktif = False; ev_menu_rect_cache=None
                    elif hayvan_rect.collidepoint(event.pos) and not (hayvan_state == HAYVAN_STATE_GOING_HOME):
                        hayvan_surukleniyor = True; top_surukleniyor = False; ev_surukleniyor = False; fare_offset_x = hayvan_rect.x - event.pos[0]; fare_offset_y = hayvan_rect.y - event.pos[1]; hedef_konum = None; is_chasing_ball = False; hayvan_state = HAYVAN_STATE_IDLE
                        hayvan_click_times.append(current_time); recent_clicks = [t for t in hayvan_click_times if current_time - t < MULTI_CLICK_INTERVAL]
                        if len(recent_clicks) >= MULTI_CLICK_COUNT: print(f"{MULTI_CLICK_COUNT} hızlı tıklama algılandı!"); hayvan_mutluluk = min(100, hayvan_mutluluk + 15); create_particles(hayvan_rect.center, 15, color=PARTICLE_BLUE); hayvan_state = HAYVAN_STATE_HAPPY; hayvan_state_timer = HAPPY_DURATION; hayvan_click_times.clear()
                        else: hayvan_click_times = deque(recent_clicks, maxlen=4)
                    elif top_ekranda and top_drag_rect.collidepoint(event.pos) and not hayvan_surukleniyor and not ev_surukleniyor: top_surukleniyor = True; hayvan_surukleniyor = False; ev_surukleniyor = False; fare_offset_x = top_merkez[0] - event.pos[0]; fare_offset_y = top_merkez[1] - event.pos[1]; top_hiz_x = 0; top_hiz_y = 0; is_chasing_ball = False; top_angle = 0
                    elif ev_rect.collidepoint(event.pos) and not hayvan_surukleniyor and not top_surukleniyor: ev_surukleniyor = True; hayvan_surukleniyor = False; top_surukleniyor = False; fare_offset_x = ev_rect.x - event.pos[0]; fare_offset_y = ev_rect.y - event.pos[1]; hedef_konum = None; is_chasing_ball = False
                    elif ev_rect.collidepoint(event.pos) and not ev_surukleniyor: # Eve çift tıklama
                        if current_time - son_ev_tiklama_zamani < cift_tiklama_suresi: hedef_konum = ev_rect.center; hayvan_surukleniyor = False; top_surukleniyor = False; ev_surukleniyor = False; is_chasing_ball = False; hayvan_state = HAYVAN_STATE_GOING_HOME; hayvan_anim_index = 0
                        son_ev_tiklama_zamani = current_time
                    elif ev_rect.collidepoint(event.pos): son_ev_tiklama_zamani = current_time
                    else: hayvan_menu_aktif = False; hayvan_menu_rect_cache = None; ev_menu_aktif = False; ev_menu_rect_cache = None
            elif event.button == 3:
                 if ayarlar_menu_aktif: continue
                 if hayvan_rect.collidepoint(event.pos): hayvan_menu_aktif = True; ev_menu_aktif = False; menu_konumu = event.pos; #...
                 elif ev_rect.collidepoint(event.pos): ev_menu_aktif = True; hayvan_menu_aktif = False; menu_konumu = event.pos; #...
                 else: hayvan_menu_aktif = False; hayvan_menu_rect_cache = None; ev_menu_aktif = False; ev_menu_rect_cache = None
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                scrollbar_dragging = False # Kaydırma çubuğu sürüklemeyi bitir
                if hayvan_surukleniyor: hayvan_surukleniyor = False; hayvan_state = HAYVAN_STATE_IDLE; #...
                if top_surukleniyor: top_surukleniyor = False; #...
                if ev_surukleniyor: ev_surukleniyor = False; #...
        elif event.type == pygame.MOUSEMOTION:
            if scrollbar_dragging and assets_scrollbar_rect:
                mouse_y = event.pos[1]; new_handle_y = mouse_y - scrollbar_drag_offset_y; new_handle_y = max(assets_scrollbar_rect.y, min(new_handle_y, assets_scrollbar_rect.bottom - assets_scrollbar_handle_rect.height))
                view_height = icerik_alani_rect.height - 2 * icerik_padding; max_scroll = max(0, assets_content_height - view_height); scrollable_track_height = assets_scrollbar_rect.height - assets_scrollbar_handle_rect.height
                if scrollable_track_height > 0: scroll_ratio = (new_handle_y - assets_scrollbar_rect.y) / scrollable_track_height; assets_scroll_y = scroll_ratio * max_scroll
                else: assets_scroll_y = 0
                assets_scroll_y = max(0, min(assets_scroll_y, max_scroll))
            elif hayvan_surukleniyor: hayvan_rect.x = event.pos[0] + fare_offset_x; hayvan_rect.y = event.pos[1] + fare_offset_y
            elif top_surukleniyor and top_ekranda: top_merkez[0] = event.pos[0] + fare_offset_x; top_merkez[1] = event.pos[1] + fare_offset_y; top_drag_rect.center = top_merkez
            elif ev_surukleniyor: ev_rect.x = event.pos[0] + fare_offset_x; ev_rect.y = event.pos[1] + fare_offset_y

    # --- Oyun Mantığı ---
    # ... (Aynı kaldı) ...
    oyun_duraklatildi = ayarlar_menu_aktif
    if not oyun_duraklatildi:
        is_moving = False
        if not hayvan_surukleniyor: hayvan_mutluluk = max(0, hayvan_mutluluk - MUTLULUK_DECAY_RATE * delta_time / 1000.0); hayvan_aclik = max(0, hayvan_aclik - ACLIK_DECAY_RATE * delta_time / 1000.0)
        if hayvan_state != HAYVAN_STATE_SLEEPING:
            if hayvan_aclik < 20 or hayvan_mutluluk < 5:
                if hayvan_state != HAYVAN_STATE_ANGRY: hayvan_state = HAYVAN_STATE_ANGRY; hedef_konum = None; is_chasing_ball = False
            elif hayvan_mutluluk < 10:
                 if hayvan_state != HAYVAN_STATE_SAD: hayvan_state = HAYVAN_STATE_SAD; hedef_konum = None; is_chasing_ball = False
            elif hayvan_state in [HAYVAN_STATE_ANGRY, HAYVAN_STATE_SAD]:
                 if hayvan_aclik >= 20 and hayvan_mutluluk >= 10: hayvan_state = HAYVAN_STATE_IDLE
        if hedef_konum and not is_chasing_ball and hayvan_state not in [HAYVAN_STATE_SLEEPING, HAYVAN_STATE_ANGRY, HAYVAN_STATE_SAD, HAYVAN_STATE_HAPPY, HAYVAN_STATE_SITTING_LEFT, HAYVAN_STATE_SITTING_RIGHT, HAYVAN_STATE_BACK, HAYVAN_STATE_SMILE, HAYVAN_STATE_KIPS, HAYVAN_STATE_SMILE2]:
            if hayvan_state == HAYVAN_STATE_WALKING or hayvan_state == HAYVAN_STATE_GOING_HOME:
                hedef_x, hedef_y = hedef_konum; hayvan_merkez_x, hayvan_merkez_y = hayvan_rect.center; dx = hedef_x - hayvan_merkez_x; dy = hedef_y - hayvan_merkez_y; mesafe = math.hypot(dx, dy)
                if mesafe > hareket_hizi: yon_x = dx / mesafe; yon_y = dy / mesafe; hayvan_rect.x += yon_x * hareket_hizi; hayvan_rect.y += yon_y * hareket_hizi; hayvan_direction = "right" if dx > 0 else "left"; is_moving = True
                else: hayvan_state = HAYVAN_STATE_IDLE; hedef_konum = None;
                if hayvan_rect.colliderect(ev_rect): hayvan_sleep_timer = 0
        elif hayvan_state not in [HAYVAN_STATE_ANGRY, HAYVAN_STATE_SAD, HAYVAN_STATE_SLEEPING, HAYVAN_STATE_HAPPY] and not hayvan_surukleniyor and top_ekranda:
            hedef_x, hedef_y = top_merkez; hayvan_merkez_x, hayvan_merkez_y = hayvan_rect.center; dx = hedef_x - hayvan_merkez_x; dy = hedef_y - hayvan_merkez_y; mesafe = math.hypot(dx, dy); yakalama_mesafesi = hayvan_rect.width / 2 + top_yaricap + 5
            if hayvan_state in [HAYVAN_STATE_IDLE, HAYVAN_STATE_SITTING_LEFT, HAYVAN_STATE_SITTING_RIGHT, HAYVAN_STATE_BACK, HAYVAN_STATE_SMILE, HAYVAN_STATE_KIPS, HAYVAN_STATE_SMILE2]:
                 hayvan_direction = "right" if dx > 0 else "left"; hayvan_state = HAYVAN_STATE_TRIGGERED_RIGHT if hayvan_direction == "right" else HAYVAN_STATE_TRIGGERED_LEFT; hayvan_state_timer = TRIGGER_DURATION; hedef_konum = top_merkez; is_chasing_ball = True
            elif hayvan_state in [HAYVAN_STATE_WALKING, HAYVAN_STATE_TRIGGERED_LEFT, HAYVAN_STATE_TRIGGERED_RIGHT]:
                 if not is_chasing_ball or not hedef_konum: hayvan_direction = "right" if dx > 0 else "left"; hayvan_state = HAYVAN_STATE_TRIGGERED_RIGHT if hayvan_direction == "right" else HAYVAN_STATE_TRIGGERED_LEFT; hayvan_state_timer = TRIGGER_DURATION; hedef_konum = top_merkez; is_chasing_ball = True
                 else:
                    hedef_konum = top_merkez; hayvan_direction = "right" if dx > 0 else "left"
                    if hayvan_state in [HAYVAN_STATE_TRIGGERED_LEFT, HAYVAN_STATE_TRIGGERED_RIGHT]:
                        hayvan_state_timer -= delta_time
                        if hayvan_state_timer <= 0: hayvan_state = HAYVAN_STATE_WALKING; hayvan_anim_index = 0; hayvan_anim_timer = 0
                    if hayvan_state == HAYVAN_STATE_WALKING:
                        if mesafe > yakalama_mesafesi: yon_x = dx / mesafe; yon_y = dy / mesafe; kovalama_hizi_carpani = 0.8; hayvan_rect.x += yon_x * hareket_hizi * kovalama_hizi_carpani; hayvan_rect.y += yon_y * hareket_hizi * kovalama_hizi_carpani; is_moving = True
                        else: create_particles(hayvan_rect.center, 15); top_ekranda = False; hedef_konum = None; is_chasing_ball = False; hayvan_state = HAYVAN_STATE_IDLE; top_hiz_x = 0; top_hiz_y = 0
        elif hayvan_state == HAYVAN_STATE_HAPPY:
            hayvan_state_timer -= delta_time
            if hayvan_state_timer <= 0: hayvan_state = HAYVAN_STATE_IDLE
        elif hayvan_state == HAYVAN_STATE_IDLE and not hayvan_surukleniyor:
            hayvan_idle_timer += delta_time
            if ev_rect.collidepoint(hayvan_rect.center):
                hayvan_sleep_timer += delta_time
                if hayvan_sleep_timer >= SLEEP_THRESHOLD: hayvan_state = HAYVAN_STATE_SLEEPING
            else: hayvan_sleep_timer = 0
            if hayvan_idle_timer >= IDLE_ACTION_THRESHOLD:
                hayvan_idle_timer = 0
                if not ev_rect.collidepoint(hayvan_rect.center) and random.random() < 0.3:
                    wander_target_x = random.randint(hayvan_rect.width // 2, SCREEN_WIDTH - hayvan_rect.width // 2)
                    wander_target_y = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - hayvan_rect.height)
                    hedef_konum = (wander_target_x, wander_target_y); hayvan_state = HAYVAN_STATE_WALKING; is_chasing_ball = False; hayvan_anim_index = 0; hayvan_anim_timer = 0
                else:
                    possible_actions = [HAYVAN_STATE_SITTING_LEFT, HAYVAN_STATE_SITTING_RIGHT, HAYVAN_STATE_BACK, HAYVAN_STATE_SMILE, HAYVAN_STATE_KIPS, HAYVAN_STATE_SMILE2, HAYVAN_STATE_IDLE]
                    action = random.choice(possible_actions)
                    if action != HAYVAN_STATE_IDLE: hayvan_state = action; hayvan_state_timer = SHORT_ACTION_DURATION if action in [HAYVAN_STATE_SMILE, HAYVAN_STATE_KIPS, HAYVAN_STATE_SMILE2] else SIT_BACK_DURATION
        elif hayvan_state in [HAYVAN_STATE_SITTING_LEFT, HAYVAN_STATE_SITTING_RIGHT, HAYVAN_STATE_BACK, HAYVAN_STATE_SMILE, HAYVAN_STATE_KIPS, HAYVAN_STATE_SMILE2, HAYVAN_STATE_ANGRY, HAYVAN_STATE_SAD]:
             if hayvan_state_timer > 0:
                 hayvan_state_timer -= delta_time
                 if hayvan_state_timer <= 0:
                     if hayvan_state in [HAYVAN_STATE_ANGRY, HAYVAN_STATE_SAD]:
                          if hayvan_aclik >= 20 and hayvan_mutluluk >= 10: hayvan_state = HAYVAN_STATE_IDLE
                     else: hayvan_state = HAYVAN_STATE_IDLE
        elif hayvan_state == HAYVAN_STATE_SLEEPING:
            if ev_surukleniyor: hayvan_state = HAYVAN_STATE_ANGRY; hayvan_state_timer = ANGRY_DURATION
            elif hayvan_surukleniyor: hayvan_state = HAYVAN_STATE_IDLE

        if is_moving and img_walk_frames:
            hayvan_anim_timer += delta_time
            if hayvan_anim_timer >= HAYVAN_ANIM_SPEED: hayvan_anim_timer = 0; hayvan_anim_index = (hayvan_anim_index + 1) % len(img_walk_frames)
        if top_ekranda and not top_surukleniyor:
            angle_change = top_hiz_x * TOP_ROTATION_FACTOR * delta_time / 1000.0; top_angle += angle_change; top_angle %= 360
            top_hiz_y += yercekimi; top_merkez[1] += top_hiz_y
            if top_merkez[1] + top_yaricap > SCREEN_HEIGHT: top_merkez[1] = SCREEN_HEIGHT - top_yaricap; top_hiz_y *= (0 if abs(top_hiz_y) < 1.5 else sekme_faktoru)
            elif top_merkez[1] - top_yaricap < 0: top_merkez[1] = top_yaricap; top_hiz_y *= sekme_faktoru
            top_merkez[0] += top_hiz_x
            if top_merkez[0] + top_yaricap > SCREEN_WIDTH: top_merkez[0] = SCREEN_WIDTH - top_yaricap; top_hiz_x *= yatay_sekme_faktoru
            elif top_merkez[0] - top_yaricap < 0: top_merkez[0] = top_yaricap; top_hiz_x *= yatay_sekme_faktoru
            if abs(top_hiz_x) < 0.1 and abs(top_hiz_y) == 0 and top_merkez[1] + top_yaricap >= SCREEN_HEIGHT -1 : top_hiz_x = 0
            top_drag_rect.center = (int(top_merkez[0]), int(top_merkez[1]))

    # Parçacıkları Güncelle
    for i in range(len(particles) - 1, -1, -1):
        particles[i].update() # Düzeltildi
        if particles[i].lifespan <= 0 or particles[i].size <=0: # Düzeltildi
             particles.pop(i) # Düzeltildi

    # İmleç yanıp sönme zamanlayıcısı
    if current_time - cursor_blink_timer > 500: cursor_visible = not cursor_visible; cursor_blink_timer = current_time


    # --- Çizim Kodları ---
    screen.fill(BACKGROUND_COLOR)

    # Ev
    if ev_image_scaled: screen.blit(ev_image_scaled, ev_rect.topleft)
    else: pygame.draw.rect(screen, ev_color, ev_rect)
    if current_settings["show_object_names"]:
        ev_text_surface=font.render(get_text("house", current_language),True,TEXT_COLOR if sum(ev_color)>300 else WHITE)
        ev_text_rect=ev_text_surface.get_rect(center=(ev_rect.centerx,ev_rect.top-15))
        screen.blit(ev_text_surface,ev_text_rect)

    # Hayvanı Çiz
    # ... (Hayvan çizim mantığı aynı) ...
    current_hayvan_image = None; flip_horizontal = (hayvan_direction == "left")
    if hayvan_state == HAYVAN_STATE_ANGRY: current_hayvan_image = img_angry
    elif hayvan_state == HAYVAN_STATE_SAD: current_hayvan_image = img_sad
    elif hayvan_state == HAYVAN_STATE_HAPPY: current_hayvan_image = img_happy
    elif hayvan_state == HAYVAN_STATE_SLEEPING: current_hayvan_image = img_sleep; flip_horizontal = False
    elif hayvan_state == HAYVAN_STATE_IDLE: current_hayvan_image = img_idle
    elif hayvan_state == HAYVAN_STATE_SITTING_LEFT: current_hayvan_image = img_sit_left; flip_horizontal = False
    elif hayvan_state == HAYVAN_STATE_SITTING_RIGHT: current_hayvan_image = img_sit_right; flip_horizontal = False
    elif hayvan_state == HAYVAN_STATE_BACK: current_hayvan_image = img_back
    elif hayvan_state == HAYVAN_STATE_TRIGGERED_LEFT: current_hayvan_image = img_trigger_left; flip_horizontal = False
    elif hayvan_state == HAYVAN_STATE_TRIGGERED_RIGHT: current_hayvan_image = img_trigger_right; flip_horizontal = False
    elif hayvan_state == HAYVAN_STATE_SMILE: current_hayvan_image = img_smile
    elif hayvan_state == HAYVAN_STATE_KIPS: current_hayvan_image = img_kips
    elif hayvan_state == HAYVAN_STATE_SMILE2: current_hayvan_image = img_smile_2
    elif hayvan_state == HAYVAN_STATE_WALKING and img_walk_frames: current_hayvan_image = img_walk_frames[hayvan_anim_index]
    elif hayvan_state == HAYVAN_STATE_GOING_HOME and img_walk_frames: current_hayvan_image = img_walk_frames[hayvan_anim_index]
    else: current_hayvan_image = img_idle
    if current_hayvan_image:
        image_to_draw = current_hayvan_image
        if flip_horizontal and hayvan_state not in [HAYVAN_STATE_SITTING_LEFT, HAYVAN_STATE_SITTING_RIGHT, HAYVAN_STATE_TRIGGERED_LEFT, HAYVAN_STATE_TRIGGERED_RIGHT, HAYVAN_STATE_SLEEPING, HAYVAN_STATE_BACK]: image_to_draw = pygame.transform.flip(current_hayvan_image, True, False)
        screen.blit(image_to_draw, hayvan_rect.topleft)
    else: pygame.draw.rect(screen, hayvan_color, hayvan_rect)

    # Hayvan Etiketi
    if current_settings["show_object_names"]:
        hayvan_etiket_metni = hayvan_ismi if hayvan_ismi else get_text("pet", current_language)
        hayvan_text_surface=font.render(hayvan_etiket_metni,True,TEXT_COLOR)
        hayvan_text_rect=hayvan_text_surface.get_rect(center=(hayvan_rect.centerx,hayvan_rect.top-15))
        screen.blit(hayvan_text_surface,hayvan_text_rect)

    # Top ve Parçacıklar
    if top_ekranda:
        if img_ball:
            rotated_ball_image = pygame.transform.rotate(img_ball, -top_angle)
            rotated_ball_rect = rotated_ball_image.get_rect(center=(int(top_merkez[0]), int(top_merkez[1])))
            screen.blit(rotated_ball_image, rotated_ball_rect.topleft)
        else:
            pygame.draw.circle(screen,top_color,(int(top_merkez[0]),int(top_merkez[1])),top_yaricap)
        if not top_surukleniyor and current_settings["show_object_names"]:
             top_text_surface = font.render(get_text("ball", current_language), True, TEXT_COLOR)
             top_text_rect = top_text_surface.get_rect(center=(top_drag_rect.centerx, top_drag_rect.top - 15))
             screen.blit(top_text_surface, top_text_rect)
    for particle in particles: particle.draw(screen)


    # --- Menüler --- DÜZELTİLDİ (Syntax) ---
    if not ayarlar_menu_aktif:
        # Hayvan Sağ Tık Menüsü
        if hayvan_menu_aktif:
             mutluluk_text = f"{get_text('happiness', current_language)}: {int(hayvan_mutluluk)}"
             aclik_text = f"{get_text('hunger', current_language)}: {int(hayvan_aclik)}"
             uyku_text = f"{get_text('sleep', current_language)}: {int(hayvan_uyku)}"
             mutluluk_surf = menu_font.render(mutluluk_text, True, TEXT_COLOR)
             aclik_surf = menu_font.render(aclik_text, True, TEXT_COLOR)
             uyku_surf = menu_font.render(uyku_text, True, TEXT_COLOR)
             padding = 10
             satir_yuksekligi = mutluluk_surf.get_height() + 5
             menu_yukseklik = padding * 2 + satir_yuksekligi * 3 - 5
             mk_x, mk_y = menu_konumu
             if mk_y + menu_yukseklik > SCREEN_HEIGHT:
                 mk_y = SCREEN_HEIGHT - menu_yukseklik
             menu_rect = pygame.Rect(mk_x, mk_y, menu_genislik, menu_yukseklik)
             hayvan_menu_rect_cache = menu_rect
             pygame.draw.rect(screen, GRAY, menu_rect, border_radius=5)
             screen.blit(mutluluk_surf, (menu_rect.left + padding, menu_rect.top + padding))
             screen.blit(aclik_surf, (menu_rect.left + padding, menu_rect.top + padding + satir_yuksekligi))
             screen.blit(uyku_surf, (menu_rect.left + padding, menu_rect.top + padding + satir_yuksekligi * 2))
        else:
             hayvan_menu_rect_cache = None

        # Ev Sağ Tık Menüsü
        if ev_menu_aktif:
             getir_text = get_text("get_ball", current_language)
             ayarlar_text = get_text("settings", current_language)
             yemek_text = get_text("feed", current_language)
             getir_surf = menu_font.render(getir_text, True, TEXT_COLOR)
             ayarlar_surf = menu_font.render(ayarlar_text, True, TEXT_COLOR)
             yemek_surf = menu_font.render(yemek_text, True, TEXT_COLOR)
             padding = 10
             button_padding = 5
             button_width = ev_menu_genislik - 2 * padding
             button_height = max(getir_surf.get_height(), ayarlar_surf.get_height(), yemek_surf.get_height()) + padding // 2
             ev_menu_yukseklik = padding * 2 + button_height * 3 + button_padding * 2
             mk_x, mk_y = menu_konumu
             if mk_y + ev_menu_yukseklik > SCREEN_HEIGHT:
                 mk_y = SCREEN_HEIGHT - ev_menu_yukseklik
             ev_menu_rect = pygame.Rect(mk_x, mk_y, ev_menu_genislik, ev_menu_yukseklik)
             ev_menu_rect_cache = ev_menu_rect
             pygame.draw.rect(screen, GRAY, ev_menu_rect, border_radius=5)
             topu_getir_button_rect = pygame.Rect(ev_menu_rect.left + padding, ev_menu_rect.top + padding, button_width, button_height)
             pygame.draw.rect(screen, LIGHT_GRAY, topu_getir_button_rect, border_radius=3)
             getir_text_rect = getir_surf.get_rect(center=topu_getir_button_rect.center)
             screen.blit(getir_surf, getir_text_rect)
             ayarlar_button_y = topu_getir_button_rect.bottom + button_padding
             ayarlar_button_rect = pygame.Rect(ev_menu_rect.left + padding, ayarlar_button_y, button_width, button_height)
             pygame.draw.rect(screen, LIGHT_GRAY, ayarlar_button_rect, border_radius=3)
             ayarlar_text_rect = ayarlar_surf.get_rect(center=ayarlar_button_rect.center)
             screen.blit(ayarlar_surf, ayarlar_text_rect)
             yemek_button_y = ayarlar_button_rect.bottom + button_padding
             yemek_ver_button_rect = pygame.Rect(ev_menu_rect.left + padding, yemek_button_y, button_width, button_height)
             pygame.draw.rect(screen, LIGHT_GRAY, yemek_ver_button_rect, border_radius=3)
             yemek_text_rect = yemek_surf.get_rect(center=yemek_ver_button_rect.center)
             screen.blit(yemek_surf, yemek_text_rect)
        else:
             ev_menu_rect_cache = None


    # --- Ayarlar Menüsü Çizimi ---
    if ayarlar_menu_aktif:
        # ... (Ayarlar menüsü çizimi aynı) ...
        panel_width = 650; panel_height = 400; panel_x = (SCREEN_WIDTH - panel_width) // 2; panel_y = (SCREEN_HEIGHT - panel_height) // 2
        ayarlar_panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height); pygame.draw.rect(screen, DARK_GRAY, ayarlar_panel_rect, border_radius=15)
        sekme_alani_yukseklik = 40; sekme_alani_rect = pygame.Rect(ayarlar_panel_rect.left, ayarlar_panel_rect.top, ayarlar_panel_rect.width, sekme_alani_yukseklik); pygame.draw.rect(screen, SETTINGS_TAB_BG, sekme_alani_rect, border_top_left_radius=15, border_top_right_radius=15)
        sekmeler_keys = ["pet", "house", "ball", "assets", "game_settings"]; sekme_genisligi = ayarlar_panel_rect.width // len(sekmeler_keys); ayarlar_sekme_butonlari = {}
        for i, sekme_key in enumerate(sekmeler_keys): sekme_text = get_text(sekme_key, current_language); sekme_rect = pygame.Rect(ayarlar_panel_rect.left + i * sekme_genisligi, ayarlar_panel_rect.top, sekme_genisligi, sekme_alani_yukseklik); ayarlar_sekme_butonlari[sekme_key] = sekme_rect; aktif_mi = (sekme_key == aktif_ayar_sekmesi); sekme_bg_color = SETTINGS_TAB_ACTIVE_BG if aktif_mi else SETTINGS_TAB_BG; radius_args = {"border_top_left_radius": 15} if i == 0 else {"border_top_right_radius": 15} if i == len(sekmeler_keys) - 1 else {}; pygame.draw.rect(screen, sekme_bg_color, sekme_rect, **radius_args); sekme_surf = settings_tab_font.render(sekme_text, True, SETTINGS_TEXT_COLOR); sekme_text_rect = sekme_surf.get_rect(center=sekme_rect.center); screen.blit(sekme_surf, sekme_text_rect);
        if i < len(sekmeler_keys) - 1: pygame.draw.line(screen, DARK_GRAY, sekme_rect.topright, (sekme_rect.right, sekme_rect.bottom), 2)
        icerik_alani_rect = pygame.Rect(ayarlar_panel_rect.left, sekme_alani_rect.bottom, ayarlar_panel_rect.width, ayarlar_panel_rect.height - sekme_alani_yukseklik); pygame.draw.rect(screen, SETTINGS_BG_COLOR, icerik_alani_rect, border_bottom_left_radius=15, border_bottom_right_radius=15); icerik_padding = 25; scrollbar_width = 15; scrollbar_padding = 5

        if aktif_ayar_sekmesi == "pet": #... (Hayvan sekmesi çizimi aynı)
            gorsel_alan_rect = pygame.Rect(icerik_alani_rect.left + icerik_padding, icerik_alani_rect.top + icerik_padding, 100, 100);
            if img_idle: img_rect = img_idle.get_rect(center=gorsel_alan_rect.center); screen.blit(img_idle, img_rect)
            else: pygame.draw.rect(screen, hayvan_color, gorsel_alan_rect, border_radius=5)
            pygame.draw.rect(screen, LIGHT_GRAY, gorsel_alan_rect, width=2, border_radius=5); bilgi_alani_x = gorsel_alan_rect.right + icerik_padding; bilgi_alani_y = gorsel_alan_rect.top; current_y = bilgi_alani_y
            isim_label_surf = settings_label_font.render(f"{get_text('name', current_language)}:", True, SETTINGS_TEXT_COLOR); screen.blit(isim_label_surf, (bilgi_alani_x, current_y)); isim_deger_x = bilgi_alani_x + isim_label_surf.get_width() + 10; isim_metni = aktif_metin_girisi if isim_duzenleme_aktif else hayvan_ismi; isim_deger_surf = settings_font.render(isim_metni, True, WHITE); input_rect_width = max(150, isim_deger_surf.get_width() + 20); hayvan_isim_input_rect = pygame.Rect(isim_deger_x - 5, current_y - 5, input_rect_width, isim_deger_surf.get_height() + 10);
            if isim_duzenleme_aktif: pygame.draw.rect(screen, INPUT_ACTIVE_BORDER, hayvan_isim_input_rect, width=1, border_radius=3); screen.blit(isim_deger_surf, (isim_deger_x, current_y));
            if isim_duzenleme_aktif and cursor_visible: cursor_x = isim_deger_x + isim_deger_surf.get_width() + 2; cursor_y = current_y; pygame.draw.line(screen, WHITE, (cursor_x, cursor_y), (cursor_x, cursor_y + isim_deger_surf.get_height()), 1)
            else: screen.blit(isim_deger_surf, (isim_deger_x, current_y))
            duzenle_text = get_text("edit", current_language); duzenle_surf = menu_font.render(duzenle_text, True, TEXT_COLOR); duzenle_button_width = duzenle_surf.get_width() + 10; hayvan_isim_duzenle_button_rect = pygame.Rect(hayvan_isim_input_rect.right + 10, hayvan_isim_input_rect.top, duzenle_button_width, hayvan_isim_input_rect.height); pygame.draw.rect(screen, LIGHT_GRAY if not isim_duzenleme_aktif else GRAY, hayvan_isim_duzenle_button_rect, border_radius=3); duzenle_text_rect = duzenle_surf.get_rect(center=hayvan_isim_duzenle_button_rect.center); screen.blit(duzenle_surf, duzenle_text_rect); current_y += hayvan_isim_input_rect.height + 10
            yas_label_surf = settings_label_font.render(f"{get_text('age', current_language)}:", True, SETTINGS_TEXT_COLOR); screen.blit(yas_label_surf, (bilgi_alani_x, current_y)); yas_deger_surf = settings_font.render(str(hayvan_yas), True, WHITE); screen.blit(yas_deger_surf, (bilgi_alani_x + isim_label_surf.get_width() + 10, current_y)); current_y += yas_label_surf.get_height() + 15
            renk_label_surf = settings_label_font.render(f"{get_text('color', current_language)} (Yedek):", True, SETTINGS_TEXT_COLOR); screen.blit(renk_label_surf, (bilgi_alani_x, current_y)); renk_secenekleri = [BLUE, YELLOW, PURPLE]; renk_buton_size = 30; renk_buton_x = bilgi_alani_x + renk_label_surf.get_width() + 10; hayvan_renk_butonlari = {}
            for renk in renk_secenekleri: renk_rect = pygame.Rect(renk_buton_x, current_y - 5, renk_buton_size, renk_buton_size); hayvan_renk_butonlari[renk] = renk_rect; pygame.draw.rect(screen, renk, renk_rect, border_radius=4);
            if hayvan_color == renk: pygame.draw.rect(screen, WHITE, renk_rect, width=3, border_radius=4)
            renk_buton_x += renk_buton_size + 10
        elif aktif_ayar_sekmesi == "house": #... (Ev sekmesi çizimi aynı)
            gorsel_alan_rect = pygame.Rect(icerik_alani_rect.left + icerik_padding, icerik_alani_rect.top + icerik_padding, 100, 100);
            if ev_image_scaled: img_rect = ev_image_scaled.get_rect(center=gorsel_alan_rect.center); screen.blit(ev_image_scaled, img_rect)
            else: pygame.draw.rect(screen, ev_color, gorsel_alan_rect, border_radius=5)
            pygame.draw.rect(screen, LIGHT_GRAY, gorsel_alan_rect, width=2, border_radius=5); bilgi_alani_x = gorsel_alan_rect.right + icerik_padding; bilgi_alani_y = gorsel_alan_rect.top; current_y = bilgi_alani_y
            renk_label_surf = settings_label_font.render(f"{get_text('color', current_language)}:", True, SETTINGS_TEXT_COLOR); screen.blit(renk_label_surf, (bilgi_alani_x, current_y)); renk_secenekleri = [GREEN, ORANGE, BROWN]; renk_buton_size = 30; renk_buton_x = bilgi_alani_x + renk_label_surf.get_width() + 10; ev_renk_butonlari = {}
            for renk in renk_secenekleri: renk_rect = pygame.Rect(renk_buton_x, current_y - 5, renk_buton_size, renk_buton_size); ev_renk_butonlari[renk] = renk_rect; pygame.draw.rect(screen, renk, renk_rect, border_radius=4);
            if ev_color == renk: pygame.draw.rect(screen, WHITE, renk_rect, width=3, border_radius=4)
            renk_buton_x += renk_buton_size + 10
        elif aktif_ayar_sekmesi == "ball": #... (Top sekmesi çizimi aynı)
            gorsel_alan_rect = pygame.Rect(icerik_alani_rect.left + icerik_padding, icerik_alani_rect.top + icerik_padding, 100, 100)
            if img_ball: img_rect = img_ball.get_rect(center=gorsel_alan_rect.center); screen.blit(img_ball, img_rect)
            else: pygame.draw.circle(screen, top_color, gorsel_alan_rect.center, top_yaricap * 2)
            pygame.draw.rect(screen, LIGHT_GRAY, gorsel_alan_rect, width=2, border_radius=5); bilgi_alani_x = gorsel_alan_rect.right + icerik_padding; bilgi_alani_y = gorsel_alan_rect.top; current_y = bilgi_alani_y
            renk_label_surf = settings_label_font.render(f"{get_text('color', current_language)}:", True, SETTINGS_TEXT_COLOR); screen.blit(renk_label_surf, (bilgi_alani_x, current_y)); renk_secenekleri = [RED, BLUE, GREEN]; renk_buton_size = 30; renk_buton_x = bilgi_alani_x + renk_label_surf.get_width() + 10; top_renk_butonlari = {}
            for renk in renk_secenekleri: renk_rect = pygame.Rect(renk_buton_x, current_y - 5, renk_buton_size, renk_buton_size); top_renk_butonlari[renk] = renk_rect; pygame.draw.rect(screen, renk, renk_rect, border_radius=4);
            if top_color == renk: pygame.draw.rect(screen, WHITE, renk_rect, width=3, border_radius=4)
            renk_buton_x += renk_buton_size + 10
        elif aktif_ayar_sekmesi == "assets": # Varlıklar Sekmesi Çizimi - DÜZELTİLDİ (Syntax)
            items_per_row = 5; preview_size = (80, 80); item_padding_x = 15; item_padding_y = 10
            button_width = 70; button_height = 20; label_height = 18
            item_total_width = preview_size[0] + item_padding_x
            item_height_content = preview_size[1] + 5 + label_height + 5 + button_height # İçerik yüksekliği
            item_total_height = item_height_content + item_padding_y * 2 # Toplam öğe yüksekliği (padding dahil)

            view_rect = icerik_alani_rect.inflate(-icerik_padding*2 - scrollbar_width - scrollbar_padding, -icerik_padding*2)
            view_height = view_rect.height
            num_rows = math.ceil(len(asset_list) / items_per_row)
            assets_content_height = num_rows * item_height_content + (num_rows - 1) * item_padding_y + item_padding_y * 2 # Toplam içerik yüksekliği (düzeltildi)
            max_scroll = max(0, assets_content_height - view_height)
            assets_scrollbar_rect = None; assets_scrollbar_handle_rect = None; scrollbar_visible = max_scroll > 0
            if scrollbar_visible:
                scrollbar_height = view_height; scrollbar_x = view_rect.right + scrollbar_padding; scrollbar_y = view_rect.top
                assets_scrollbar_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
                pygame.draw.rect(screen, SETTINGS_TAB_BG, assets_scrollbar_rect, border_radius=5)
                handle_height = max(20, view_height * (view_height / assets_content_height)) if assets_content_height > 0 else view_height # Sıfıra bölme hatasını engelle
                handle_y_ratio = assets_scroll_y / max_scroll if max_scroll > 0 else 0
                handle_y = scrollbar_y + handle_y_ratio * (scrollbar_height - handle_height)
                assets_scrollbar_handle_rect = pygame.Rect(scrollbar_x, handle_y, scrollbar_width, handle_height)
                pygame.draw.rect(screen, LIGHT_GRAY, assets_scrollbar_handle_rect, border_radius=5)

            assets_surface = pygame.Surface((view_rect.width, assets_content_height), pygame.SRCALPHA); assets_surface.fill((0,0,0,0))
            start_x = item_padding_x // 2; start_y = item_padding_y // 2
            current_x = start_x; current_y = start_y; col_count = 0; assets_edit_buttons = {}

            for asset_info in asset_list:
                display_key, asset_type, default_filename, user_filename, size, global_var_name = asset_info
                current_image = None
                # Global değişken adından görseli al - DÜZELTİLDİ (Try/Except yapısı)
                if global_var_name.startswith("img_walk_frames"):
                    try:
                        index_str = global_var_name.split('[')[1].split(']')[0]
                        index = int(index_str)
                        if 0 <= index < len(img_walk_frames):
                             current_image = img_walk_frames[index]
                    except (IndexError, ValueError):
                        pass # Hata olursa None kalır
                elif global_var_name in globals():
                    current_image = globals()[global_var_name] # Düzeltildi

                preview_rect = pygame.Rect(current_x, current_y, preview_size[0], preview_size[1])
                if current_image:
                    try: img_preview = pygame.transform.scale(current_image, preview_size); assets_surface.blit(img_preview, preview_rect)
                    except: pygame.draw.rect(assets_surface, GRAY, preview_rect, border_radius=3)
                else: pygame.draw.rect(assets_surface, GRAY, preview_rect, border_radius=3)
                pygame.draw.rect(assets_surface, LIGHT_GRAY, preview_rect, 1, border_radius=3)

                label_text = default_filename; max_label_width = preview_size[0]
                if asset_label_font.size(label_text)[0] > max_label_width:
                    original_text = label_text
                    while asset_label_font.size(label_text + "...")[0] > max_label_width and len(label_text) > 0: label_text = label_text[:-1]
                    if len(label_text) < len(original_text): label_text += "..."
                label_surf = asset_label_font.render(label_text, True, SETTINGS_TEXT_COLOR)
                label_rect = label_surf.get_rect(centerx=preview_rect.centerx, top=preview_rect.bottom + 5)
                assets_surface.blit(label_surf, label_rect)

                edit_button_rect_rel = pygame.Rect(preview_rect.centerx - button_width // 2, label_rect.bottom + 5, button_width, button_height)
                button_key = global_var_name if not global_var_name.startswith("img_walk_frames") else f"walk_{default_filename.split('_')[-1].split('.')[0]}"
                edit_button_screen_rect = edit_button_rect_rel.move(view_rect.left, view_rect.top - assets_scroll_y)
                assets_edit_buttons[button_key] = edit_button_screen_rect
                pygame.draw.rect(assets_surface, LIGHT_GRAY, edit_button_rect_rel, border_radius=3)
                edit_text_surf = menu_font.render(get_text("edit", current_language), True, TEXT_COLOR)
                edit_text_rect = edit_text_surf.get_rect(center=edit_button_rect_rel.center)
                assets_surface.blit(edit_text_surf, edit_text_rect)

                col_count += 1
                if col_count >= items_per_row:
                    col_count = 0
                    current_x = start_x
                    current_y += item_height_content + item_padding_y # Düzeltildi
                else:
                    current_x += item_total_width + item_padding_x

            screen.blit(assets_surface, view_rect.topleft, (0, assets_scroll_y, view_rect.width, view_height))

        elif aktif_ayar_sekmesi == "game_settings": # Oyun Ayarları sekmesi çizimi - DÜZELTİLDİ (Syntax)
            current_y = icerik_alani_rect.top + icerik_padding
            button_width = 300
            button_height = 35
            button_x = icerik_alani_rect.centerx - button_width // 2
            button_spacing = 8
            show_names_text = get_text("show_names", current_language)
            show_names_status = f" [{'X' if current_settings['show_object_names'] else ' '}]"
            show_names_surf = menu_font.render(show_names_text + show_names_status, True, TEXT_COLOR)
            ayarlar_isim_goster_button_rect = pygame.Rect(button_x, current_y, button_width, button_height)
            pygame.draw.rect(screen, LIGHT_GRAY, ayarlar_isim_goster_button_rect, border_radius=5)
            show_names_rect = show_names_surf.get_rect(center=ayarlar_isim_goster_button_rect.center)
            screen.blit(show_names_surf, show_names_rect)
            current_y += button_height + button_spacing
            start_win_text = get_text("start_with_windows", current_language)
            start_win_status = f" [{'X' if current_settings['start_with_windows'] else ' '}]"
            win_baslat_surf = menu_font.render(start_win_text + start_win_status, True, TEXT_COLOR)
            ayarlar_windows_baslat_button_rect = pygame.Rect(button_x, current_y, button_width, button_height)
            pygame.draw.rect(screen, LIGHT_GRAY, ayarlar_windows_baslat_button_rect, border_radius=5)
            win_baslat_rect = win_baslat_surf.get_rect(center=ayarlar_windows_baslat_button_rect.center)
            screen.blit(win_baslat_surf, win_baslat_rect)
            current_y += button_height + button_spacing
            sifirla_text = get_text("reset_settings", current_language)
            sifirla_surf = menu_font.render(sifirla_text, True, TEXT_COLOR)
            ayarlar_sifirla_button_rect = pygame.Rect(button_x, current_y, button_width, button_height)
            pygame.draw.rect(screen, LIGHT_GRAY, ayarlar_sifirla_button_rect, border_radius=5)
            sifirla_rect = sifirla_surf.get_rect(center=ayarlar_sifirla_button_rect.center)
            screen.blit(sifirla_surf, sifirla_rect)
            current_y += button_height + button_spacing
            restart_text = get_text("restart_app", current_language)
            yeniden_baslat_surf = menu_font.render(restart_text, True, TEXT_COLOR)
            ayarlar_yeniden_baslat_button_rect = pygame.Rect(button_x, current_y, button_width, button_height)
            pygame.draw.rect(screen, LIGHT_GRAY, ayarlar_yeniden_baslat_button_rect, border_radius=5)
            yeniden_baslat_rect = yeniden_baslat_surf.get_rect(center=ayarlar_yeniden_baslat_button_rect.center)
            screen.blit(yeniden_baslat_surf, yeniden_baslat_rect)
            current_y += button_height + button_spacing
            lang_label_surf = settings_label_font.render(f"{get_text('language_options', current_language)}:", True, SETTINGS_TEXT_COLOR)
            lang_label_rect = lang_label_surf.get_rect(topleft=(button_x, current_y))
            screen.blit(lang_label_surf, lang_label_rect)
            current_y += lang_label_surf.get_height() + 3
            lang_button_width = 100
            lang_button_height = 30
            lang_button_x = button_x
            tr_surf = menu_font.render(get_text("turkish", current_language), True, TEXT_COLOR)
            ayarlar_dil_tr_button_rect = pygame.Rect(lang_button_x, current_y, lang_button_width, lang_button_height)
            pygame.draw.rect(screen, LIGHT_GRAY if current_language != 'tr' else GRAY, ayarlar_dil_tr_button_rect, border_radius=3)
            tr_rect = tr_surf.get_rect(center=ayarlar_dil_tr_button_rect.center)
            screen.blit(tr_surf, tr_rect)
            en_surf = menu_font.render(get_text("english", current_language), True, TEXT_COLOR)
            ayarlar_dil_en_button_rect = pygame.Rect(lang_button_x + lang_button_width + 10, current_y, lang_button_width, lang_button_height)
            pygame.draw.rect(screen, LIGHT_GRAY if current_language != 'en' else GRAY, ayarlar_dil_en_button_rect, border_radius=3)
            en_rect = en_surf.get_rect(center=ayarlar_dil_en_button_rect.center)
            screen.blit(en_surf, en_rect)

        # Kapat Butonu
        kapat_text = get_text("close", current_language)
        kapat_surf = font.render(kapat_text, True, SETTINGS_TEXT_COLOR)
        kapat_padding = 15
        ayarlar_kapat_button_rect = kapat_surf.get_rect(topright=(ayarlar_panel_rect.right - kapat_padding, ayarlar_panel_rect.top + kapat_padding))
        pygame.draw.rect(screen, RED, ayarlar_kapat_button_rect.inflate(6,6), border_radius=3)
        screen.blit(kapat_surf, ayarlar_kapat_button_rect)

    # --- Ekranı Güncelle ---
    pygame.display.flip()

# Pygame'den çıkış yap
pygame.quit()
sys.exit()
