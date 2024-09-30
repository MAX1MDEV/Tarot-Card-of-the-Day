import os
import asyncio
import time
from datetime import datetime, timedelta
import requests
from deep_translator import GoogleTranslator
from PySide6 import QtWidgets, QtCore, QtGui, QtWebEngineWidgets, QtWebEngineCore
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
import webbrowser
import random
import winreg
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import locale
from win11toast import toast
import threading
import sys
from playsound import playsound

basedir = os.path.dirname(__file__)
icon_path = os.path.join(basedir, 'icon.png')
toast_sound_path = os.path.join(basedir, 'nyanpass.mp3')

def play_sound():
    playsound(toast_sound_path)

def show_toast(title, message):
    t = threading.Thread(target=play_sound)
    t.start()
    toast(title, message, icon=icon_path, app_id="Tarot Card of the Day")

class SplashScreen(tk.Toplevel):
    def __init__(self, image_path):
        super().__init__()
        self.overrideredirect(True)
        self.geometry("200x200")
        self.center()

        self.canvas = tk.Canvas(self, width=200, height=200, bg='green', highlightthickness=0)
        self.canvas.pack()
        
        self.wm_attributes('-transparentcolor', 'green')
        
        self.image = Image.open(image_path).resize((200, 200), Image.Resampling.LANCZOS)

        mask = Image.new('L', (200, 200), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 200, 200), fill=255)

        self.image.putalpha(mask)

        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(100, 100, image=self.photo)

    def center(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (200 // 2)
        y = (screen_height // 2) - (200 // 2)
        self.geometry(f"+{x}+{y}")

class TarotCardWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.check_and_create_directory()
        self.initUI()
        self.is_link_opened = False
        #self.create_tray_icon()
        
        

    def check_and_create_directory(self):
        self.appdata_path = os.path.join(os.getenv('APPDATA'), 'MAX1MDEV', 'TarotDayCard')
        self.appdata_log_path = os.path.join(os.getenv('APPDATA'), 'MAX1MDEV', 'TarotDayCard', 'logs')
        if not os.path.exists(self.appdata_path):
            os.makedirs(self.appdata_path)
        if not os.path.exists(self.appdata_log_path):
            os.makedirs(self.appdata_log_path)

    def initUI(self):
        self.setWindowTitle("Tarot Card of the Day")
        self.setGeometry(300, 300, 400, 300)

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QtWidgets.QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.label = QtWidgets.QLabel()
        self.layout.addWidget(self.label)

        self.text_browser = QtWidgets.QTextBrowser()
        self.layout.addWidget(self.text_browser)

        self.default_button = QtWidgets.QPushButton("Обычное" if QtCore.QLocale.system().name() == 'ru_RU' else "Default")
        self.default_button.clicked.connect(self.show_default)
        self.layout.addWidget(self.default_button)

        self.meaning_button = QtWidgets.QPushButton("50/50 значение" if QtCore.QLocale.system().name() == 'ru_RU' else "50/50 meaning")
        self.meaning_button.clicked.connect(self.show_random_meaning)
        self.layout.addWidget(self.meaning_button)

        self.autostart_file = os.path.join(self.appdata_path, 'tarot_day_card_autostart.txt')
        if not os.path.exists(self.autostart_file):
            self.autostart_button = QtWidgets.QPushButton("Включить автозагрузку" if QtCore.QLocale.system().name() == 'ru_RU' else "Enable autoloading")
            self.autostart_button.clicked.connect(self.toggle_autostart)
            self.layout.addWidget(self.autostart_button)
        else:
            self.autostart_button = QtWidgets.QPushButton("Выключить автозагрузку" if QtCore.QLocale.system().name() == 'ru_RU' else "Disable autoloading")
            self.autostart_button.clicked.connect(self.toggle_autostart)
            self.layout.addWidget(self.autostart_button)
        
        self.notify_file = os.path.join(self.appdata_path, 'tarot_day_card_notify.txt')
        if not os.path.exists(self.notify_file):
            self.notification_button = QtWidgets.QPushButton("Включить уведомления" if QtCore.QLocale.system().name() == 'ru_RU' else "Enable notifications")
            self.notification_button.clicked.connect(self.notify_button)
            self.layout.addWidget(self.notification_button)
            self.Notify = False
        else:
            self.Notify = True
            self.notification_thread = QtCore.QThread()
            self.notification_worker = NotificationWorker(self.Notify)  # notify флаг как аргумент
            self.notification_worker.moveToThread(self.notification_thread)
            self.notification_thread.started.connect(self.notification_worker.run)
            self.notification_thread.start()
            self.notification_button = QtWidgets.QPushButton("Выключить уведомления" if QtCore.QLocale.system().name() == 'ru_RU' else "Disable notifications")
            self.notification_button.clicked.connect(self.notify_button)
            self.layout.addWidget(self.notification_button)
            

        self.github_button = QtWidgets.QPushButton("MAX1MDEV")
        self.github_button.clicked.connect(self.open_github)
        self.layout.addWidget(self.github_button)
        
        
        
    
    #def minimizeEvent(self, event): # функция не работает вместе с changeEvent
    #    self.hide()
    #    self.create_tray_icon()   
    
    def create_tray_icon(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon(icon_path))
        self.tray_icon.setVisible(True)
    
        tray_menu = QtWidgets.QMenu()
        restore_action = tray_menu.addAction("Восстановить" if QtCore.QLocale.system().name() == 'ru_RU' else "Restore")
        restore_action.triggered.connect(self.restore_window)
        exit_action = tray_menu.addAction("Выход" if QtCore.QLocale.system().name() == 'ru_RU' else "Exit")
        exit_action.triggered.connect(self.exit_application)
    
        tray_menu.addSeparator()
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def remove_files(self):
        os.remove(self.notify_file)
        os.remove(self.log_file)
    
    def notify_button(self):
        lang = locale.getlocale()[0]
        self.notify_file = os.path.join(self.appdata_path, 'tarot_day_card_notify.txt')
        self.log_file = os.path.join(self.appdata_log_path, 'log.txt')
        if not os.path.exists(self.notify_file):
            self.notification_button.setText("Выключить уведомления" if QtCore.QLocale.system().name() == 'ru_RU' else "Disable notifications")
            if lang == 'ru_RU' or lang == 'Russian_Russia':
                threading.Thread(target=show_toast, args=('Дневная карта таро', 'Уведомления включены!')).start()
                #show_toast('Дневная карта таро', 'Уведомления включены!')
                #toast('Дневная карта таро', 'Уведомления включены!', icon=icon_path, app_id="Tarot Card of the Day")
            else:
                threading.Thread(target=show_toast, args=('Daily Tarot Card', 'Notifications enabled!')).start()
                #show_toast('Daily Tarot Card', 'Notifications enabled!')
                #toast('Daily Tarot Card', 'Notifications enabled!', icon=icon_path, app_id="Tarot Card of the Day")
            with open(self.log_file, 'w') as f:
                f.write('notify')
            with open(self.notify_file, 'w') as f:
                f.write('Notifications enabled')
            self.Notify = True
            self.notification_thread = QtCore.QThread()
            self.notification_worker = NotificationWorker(self.Notify)
            self.notification_worker.moveToThread(self.notification_thread)
            self.notification_thread.started.connect(self.notification_worker.run)
            self.notification_thread.start()
        else:
            self.notification_button.setText("Включить уведомления" if QtCore.QLocale.system().name() == 'ru_RU' else "Enable notifications")
            if lang == 'ru_RU' or lang == 'Russian_Russia':
                threading.Thread(target=show_toast, args=('Дневная карта таро', 'Уведомления отключены!')).start()
                #show_toast('Дневная карта таро', 'Уведомления отключены!')
                #toast('Дневная карта таро', 'Уведомления отключены!', dialogue='Уведомления отключены', app_id="Tarot Card of the Day", icon=icon_path)
            else:
                threading.Thread(target=show_toast, args=('Daily Tarot Card', 'Notifications disabled!')).start()
                #show_toast('Daily Tarot Card', 'Notifications disabled!')
                #toast('Daily Tarot Card', 'Notifications disabled!', dialogue='Notifications disabled', app_id="Tarot Card of the Day", icon=icon_path)
            self.remove_files()
            self.Notify = False
            #Из-за этого крашится программа:
            #self.notification_worker.stop()
            #self.notification_thread.quit()
            #self.notification_thread.wait()
            
            
    def tray_icon_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.restore_window()

    def restore_window(self): #функция открытия приложения
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.tray_icon.hide()

    def exit_application(self): #перестраховка
        self.tray_icon.hide()
        QtWidgets.QApplication.quit()
        
    def get_tarot_card(self):
        url = "https://tarotapi.dev/api/v1/cards/random?n=1"
        response = requests.get(url)
        self.data = response.json()

    def show_default(self):
        self.get_tarot_card()
        lang = QtCore.QLocale.system().name()
        html = ""
        if lang == 'ru_RU' or lang == 'Russian_Russia':
            self.label.setText("Ваша карта дня:")
            for card in self.data["cards"]:
                self.translated_name = GoogleTranslator(source='en', target='ru').translate(card["name"])
                link_name = f"Название карты: <a href='{QtCore.QUrl.fromUserInput(f'https://www.kp.ru/woman/?s={self.translated_name}').toString()}'>{self.translated_name}</a><br><br>"
                html += link_name
                translated_meaning_up = GoogleTranslator(source='en', target='ru').translate(card["meaning_up"])
                html += f"Прямое значение: {translated_meaning_up}<br><br>"
                translated_meaning_rev = GoogleTranslator(source='en', target='ru').translate(card["meaning_rev"])
                html += f"Перевернутое значение: {translated_meaning_rev}<br><br>"
                translated_desc = GoogleTranslator(source='en', target='ru').translate(card["desc"])
                html += f"Описание: {translated_desc}<br><br>"
        else:
            self.label.setText("Your card of the day:")
            for card in self.data["cards"]:
                link_name = f"Card name: <a href='{QtGui.QUrl.fromUserInput(f'https://biddytarot.com/?s={card['name']}').toString()}'>{card['name']}</a><br><br>"
                html += link_name
                html += f"Meaning up: {card['meaning_up']}<br><br>"
                html += f"Meaning reverse: {card['meaning_rev']}<br><br>"
                html += f"Description: {card['desc']}<br><br>"
        if self.is_link_opened:
            self.text_browser.anchorClicked.disconnect(self.open_link_in_browser)
            self.is_link_opened = False
        self.text_browser.setHtml(html)
        self.text_browser.anchorClicked.connect(self.open_link_in_browser)
        self.is_link_opened = True

    
    def show_random_meaning(self):
        self.get_tarot_card()
        lang = QtCore.QLocale.system().name()
        html = ""
        if lang == 'ru_RU' or lang == 'Russian_Russia':
            self.label.setText("Ваша карта дня:")
            for card in self.data["cards"]:
                self.translated_name = GoogleTranslator(source='en', target='ru').translate(card["name"])
                link_name = f"Название карты: <a href='{QtCore.QUrl.fromUserInput(f'https://www.kp.ru/woman/?s={self.translated_name}').toString()}'>{self.translated_name}</a><br><br>"
                html += link_name
                meaning = random.choice([card["meaning_up"], card["meaning_rev"]])
                if meaning == card["meaning_up"]:
                    translated_meaning = GoogleTranslator(source='en', target='ru').translate(meaning)
                    translated_desc = GoogleTranslator(source='en', target='ru').translate(card["desc"])
                    html += f"Прямое значение: {translated_meaning}<br><br>"
                    html += f"Описание: {translated_desc}<br><br>"
                else:
                    translated_meaning = GoogleTranslator(source='en', target='ru').translate(meaning)
                    translated_desc = GoogleTranslator(source='en', target='ru').translate(card["desc"])
                    html += f"Перевернутое значение: {translated_meaning}<br><br>"
                    html += f"Описание: {translated_desc}<br><br>"
        else:
            self.label.setText("Your card of the day:")
            for card in self.data["cards"]:
                link_name = f"Card name: <a href='{QtGui.QUrl.fromUserInput(f'https://biddytarot.com/?s={card['name']}').toString()}'>{card['name']}</a><br><br>"
                html += link_name
                meaning = random.choice([card["meaning_up"], card["meaning_rev"]])
                html += f"Random meaning: {meaning}<br><br>"
                html += f"Description: {card['desc']}<br><br>"
        if self.is_link_opened:
            self.text_browser.anchorClicked.disconnect(self.open_link_in_browser)
            self.is_link_opened = False
        self.text_browser.setHtml(html)
        self.text_browser.anchorClicked.connect(self.open_link_in_browser)
        self.is_link_opened = True
    
    def open_link_in_browser(self, url):
        QDesktopServices.openUrl(url)
        # страница внутри программы не изменяется из-за того что мы используем привязку к браузеру
        self.text_browser.setHtml(self.text_browser.toHtml())
        pass
    
    def toggle_autostart(self):
        lang = locale.getlocale()[0]
        self.autostart_file = os.path.join(self.appdata_path, 'tarot_day_card_autostart.txt')
            
        if not os.path.exists(self.autostart_file):
            self.autostart_button.setText("Выключить автозагрузку" if QtCore.QLocale.system().name() == 'ru_RU' else "Disable autoloading")
            # создание файла для условия
            with open(self.autostart_file, 'w') as f:
                f.write('Auto-start enabled')
            self.add_to_autostart()
            if lang == 'ru_RU' or lang == 'Russian_Russia':
                threading.Thread(target=show_toast, args=('Дневная карта таро', 'Программа добавлена в автозагрузку!')).start()
                #show_toast('Дневная карта таро', 'Программа добавлена в автозагрузку!')
                #toast('Дневная карта таро', 'Программа добавлена в автозагрузку!', icon=icon_path, app_id="Tarot Card of the Day")
            else:
                threading.Thread(target=show_toast, args=('Дневная карта таро', 'The program has been added to autoloader!')).start()
                #show_toast('Daily Tarot Card', 'The program has been added to autoloader!')
                #toast('Daily Tarot Card', 'The program has been added to autoloader!', icon=icon_path, app_id="Tarot Card of the Day")
        else:
            self.autostart_button.setText("Включить автозагрузку" if QtCore.QLocale.system().name() == 'ru_RU' else "Enable autoloading")
            os.remove(self.autostart_file)
            self.remove_from_autostart()
            if lang == 'ru_RU' or lang == 'Russian_Russia':
                threading.Thread(target=show_toast, args=('Daily Tarot Card', 'Программа убрана из автозагрузки!')).start()
                #show_toast('Дневная карта таро', 'Программа убрана из автозагрузки!')
                #toast('Дневная карта таро', 'Программа убрана из автозагрузки!', icon=icon_path, app_id="Tarot Card of the Day")
            else:
                threading.Thread(target=show_toast, args=('Daily Tarot Card', 'The program is removed from autoloader!')).start()
                #show_toast('Daily Tarot Card', 'The program is removed from autoloader!')
                #toast('Daily Tarot Card', 'The program is removed from autoloader!', icon=icon_path, app_id="Tarot Card of the Day")
                #toast('Daily Tarot Card', 'The program is removed from autoloader!', audio=toast_sound_path, icon=icon_path, app_id="Tarot Card of the Day")
            

    def add_to_autostart(self):
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
        executable_path = os.path.dirname(sys.executable)
        executable_file = os.path.basename(sys.executable)
        autostart_path = os.path.join(executable_path, executable_file)
        winreg.SetValueEx(key, "TarotCardApp_MAX1MDEV", 0, winreg.REG_SZ, autostart_path)
        winreg.CloseKey(key)

    def remove_from_autostart(self):
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "TarotCardApp_MAX1MDEV")
        winreg.CloseKey(key)

    def open_github(self):
        webbrowser.open("https://github.com/MAX1MDEV")
    
    def closeEvent(self, event): #функция закрытия приложения
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        event.accept()

    def changeEvent(self, event): #функция сворачивания
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & QtCore.Qt.WindowMinimized:
                event.ignore()
                self.create_tray_icon()
                self.hide()

class NotificationWorker(QtCore.QObject):
    def __init__(self, notify, parent=None):
        super(NotificationWorker, self).__init__(parent)
        self.running = True
        self.Notify = notify
        
    def run(self):
        creation_date = None
        while self.running:
            if self.Notify:
                lang = locale.getlocale()[0]
                self.appdata_path = os.path.join(os.getenv('APPDATA'), 'MAX1MDEV', 'TarotDayCard')
                self.appdata_log_path = os.path.join(os.getenv('APPDATA'), 'MAX1MDEV', 'TarotDayCard', 'logs')
                self.log_file = os.path.join(self.appdata_log_path, 'log.txt')
                self.notify_file = os.path.join(self.appdata_path, 'tarot_day_card_notify.txt')
                if os.path.exists(self.notify_file):
                    if os.path.exists(self.log_file):
                        current_date = datetime.utcnow().date()
                        creation_date = datetime.fromtimestamp(os.path.getmtime(self.log_file)).date()
                        if current_date > creation_date:
                            with open(self.log_file, 'w') as f:
                                f.write('notify')
                            if lang == 'ru_RU' or lang == 'Russian_Russia':
                                threading.Thread(target=show_toast, args=('Дневная карта таро', 'Проверьте свою дневную карту!')).start()
                                #show_toast('Дневная карта таро', 'Проверьте свою дневную карту!')
                                #toast('Дневная карта таро', 'Проверьте свою дневную карту!', icon=icon_path, app_id="Tarot Card of the Day")
                            else:
                                threading.Thread(target=show_toast, args=('Daily Tarot Card', 'Check your daily tarot card!')).start()
                                #show_toast('Daily Tarot Card', 'Check your daily tarot card!')
                                #toast('Daily Tarot Card', 'Check your daily tarot card!', icon=icon_path, app_id="Tarot Card of the Day")
            time.sleep(3)

    def stop(self):
        self.running = False
    
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    splash = SplashScreen(os.path.join(basedir, 'maximdev.png'))
    splash.update()
    time.sleep(2)
    splash.destroy()
    root.destroy()
    app = QtWidgets.QApplication([])
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'icon.ico')))
    window = TarotCardWindow()
    window.show()
    app.exec()
    