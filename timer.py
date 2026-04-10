import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime, time, timedelta
import json
import os

HISTORY_FILE = os.path.join(os.path.expanduser("~"), "timer_history.json")

MONTHS = {
    "01": "Январь", "02": "Февраль", "03": "Март",
    "04": "Апрель", "05": "Май", "06": "Июнь",
    "07": "Июль", "08": "Август", "09": "Сентябрь",
    "10": "Октябрь", "11": "Ноябрь", "12": "Декабрь"
}

class MiniTimer:
    def __init__(self, root):
        self.root = root
        self.is_expanded = False
        
        # Начальный размер свернутого окна
        self.root.geometry("240x80+10+10")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#e8f5e9")

        # Константы расписания
        self.lunch_start = time(13, 0)
        self.lunch_duration = timedelta(minutes=40)
        
        self.is_running = False
        self.history = self.load_history()
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        
        if self.today_str not in self.history:
            self.history[self.today_str] = {
                "start_time": None, 
                "worked_seconds": 0,
                "force_ended": False
            }

        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        # --- МЕНЮ НАСТРОЕК (для шестеренки) ---
        self.settings_menu = tk.Menu(self.root, tearoff=0, font=("Arial", 9))
        self.settings_menu.add_command(label="✎ Забыли старт? Указать время", command=self.ask_start_time)
        self.settings_menu.add_command(label="± Корректировка отработок", command=self.ask_adjust_time)

        # --- ВЕРХНЯЯ ПАНЕЛЬ ---
        self.top_frame = tk.Frame(root, bg="#e8f5e9")
        self.top_frame.pack(fill="x", padx=5, pady=2)
        
        # Кнопка закрытия (справа)
        tk.Button(self.top_frame, text="✕", command=self.root.destroy, bg="#e8f5e9", borderwidth=0, fg="gray").pack(side="right")
        
        # Кнопки слева
        tk.Button(self.top_frame, text="☰", command=self.show_history_window, bg="#e8f5e9", borderwidth=0, font=("Arial", 11)).pack(side="left", padx=(0, 2))
        
        self.btn_settings = tk.Button(self.top_frame, text="⚙️", command=self.show_settings_menu, bg="#e8f5e9", borderwidth=0, font=("Arial", 11))
        self.btn_settings.pack(side="left", padx=(0, 2))

        self.btn_expand = tk.Button(self.top_frame, text="▼", command=self.toggle_expand, bg="#e8f5e9", borderwidth=0)
        self.btn_expand.pack(side="left")

        # Основной таймер
        self.lbl_main_status = tk.Label(root, text="Ожидание...", bg="#e8f5e9", font=("Arial", 9))
        self.lbl_main_status.pack()
        self.lbl_main_time = tk.Label(root, text="00:00:00", bg="#e8f5e9", font=("Courier", 16, "bold"))
        self.lbl_main_time.pack()

        # --- СКРЫТАЯ ЧАСТЬ (управление таймером) ---
        self.extra_frame = tk.Frame(root, bg="#e8f5e9")
        
        ttk.Separator(self.extra_frame, orient='horizontal').pack(fill='x', pady=5)
        
        self.lbl_extra = tk.Label(self.extra_frame, text="", bg="#e8f5e9", font=("Arial", 9))
        self.lbl_extra.pack()
        
        self.btn_start = tk.Button(self.extra_frame, text="▶ Начать", command=self.start_timer, bg="#a5d6a7", relief="flat", width=15)
        self.btn_start.pack(pady=5)
        self.btn_stop = tk.Button(self.extra_frame, text="⏸ Стоп", command=self.stop_timer, bg="#ef9a9a", relief="flat", width=15, state="disabled")
        self.btn_stop.pack(pady=2)

        self.lbl_stats = tk.Label(self.extra_frame, text="Отработано: 00:00:00", bg="#e8f5e9", font=("Arial", 9, "italic"))
        self.lbl_stats.pack(pady=5)

        # --- БЛОК БАЛАНСА ---
        self.frame_balance = tk.Frame(self.extra_frame, bg="white", highlightbackground="#c8e6c9", highlightthickness=1)
        self.frame_balance.pack(fill="x", padx=15, pady=(5, 10))
        
        self.lbl_bal_title = tk.Label(self.frame_balance, text="ДОРАБОТАТЬ:", bg="white", font=("Arial", 8, "bold"), fg="#1565c0")
        self.lbl_bal_title.pack(pady=(5, 0))
        self.lbl_bal_time = tk.Label(self.frame_balance, text="00:00:00", bg="white", font=("Courier", 18, "bold"), fg="#1565c0")
        self.lbl_bal_time.pack(pady=(0, 5))

        # --- ЗАВЕРШЕНИЕ ДНЯ (в самом низу) ---
        self.btn_end_day = tk.Button(self.extra_frame, text="🏁 Завершить день", command=self.force_end_day, bg="#ffcdd2", fg="#c62828", relief="flat", font=("Arial", 9, "bold"), width=22)
        self.btn_end_day.pack(pady=(0, 10))

        self.last_tick = None
        self.update_loop()

    def show_settings_menu(self):
        # Показываем меню прямо под шестеренкой
        x = self.btn_settings.winfo_rootx()
        y = self.btn_settings.winfo_rooty() + self.btn_settings.winfo_height()
        self.settings_menu.tk_popup(x, y)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        if not self.is_expanded:
            self.extra_frame.pack_forget()
            self.btn_expand.config(text="▼")
            self.root.geometry("240x80")
        else:
            self.extra_frame.pack(fill="both", expand=True)
            self.btn_expand.config(text="▲")
            # Автоматический подсчет высоты
            self.root.update_idletasks()
            req_height = self.root.winfo_reqheight()
            self.root.geometry(f"240x{req_height}")

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f: return json.load(f)
            except Exception: return {}
        return {}

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w") as f: json.dump(self.history, f, indent=4)
        except Exception: pass

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def start_timer(self):
        if self.history[self.today_str].get("force_ended", False):
            self.history[self.today_str]["force_ended"] = False
            
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        if not self.history[self.today_str]["start_time"]:
            self.history[self.today_str]["start_time"] = datetime.now().strftime("%H:%M")
        self.last_tick = datetime.now()

    def stop_timer(self):
        self.is_running = False
        self.btn_start.config(state="normal", text="▶ Продолжить")
        self.btn_stop.config(state="disabled")
        self.save_history()

    def force_end_day(self):
        if messagebox.askyesno("Завершение дня", "Вы точно хотите досрочно завершить рабочий день?", parent=self.root):
            self.stop_timer()
            self.history[self.today_str]["force_ended"] = True
            self.save_history()
            self.update_loop(force_update=True)

    def ask_start_time(self):
        t = simpledialog.askstring("Старт", "Когда вы начали? (ЧЧ:ММ):", parent=self.root)
        if t:
            try:
                h, m = map(int, t.replace(".", ":").split(':'))
                now = datetime.now()
                start = now.replace(hour=h, minute=m, second=0)
                worked = (now - start).total_seconds()
                
                l_s = datetime.combine(now.date(), self.lunch_start)
                if start < l_s and now > (l_s + self.lunch_duration):
                    worked -= self.lunch_duration.total_seconds()
                    
                self.history[self.today_str]["worked_seconds"] = max(0, worked)
                self.history[self.today_str]["start_time"] = f"{h:02d}:{m:02d}"
                self.history[self.today_str]["force_ended"] = False 
                
                if not self.is_running: self.start_timer()
                self.save_history()
            except: pass

    def ask_adjust_time(self):
        v = simpledialog.askstring("Коррекция", "Часов добавить/вычесть (напр. 1 или -0.5):", parent=self.root)
        if v:
            try:
                self.history[self.today_str]["worked_seconds"] += float(v.replace(',', '.')) * 3600
                self.save_history()
            except: pass

    def get_day_config(self, dt):
        is_friday = dt.weekday() == 4
        end_t = time(17, 0) if is_friday else time(18, 0)
        norm = (8 * 3600 - 40 * 60) if is_friday else (9 * 3600 - 40 * 60)
        return end_t, norm

    def update_loop(self, force_update=False):
        now = datetime.now()
        
        if self.is_running and self.last_tick:
            self.history[self.today_str]["worked_seconds"] += (now - self.last_tick).total_seconds()
            self.last_tick = now
            if int(now.timestamp()) % 10 == 0: self.save_history()

        end_time_obj, daily_norm = self.get_day_config(now)
        l_start = datetime.combine(now.date(), self.lunch_start)
        l_end = l_start + self.lunch_duration
        d_end = datetime.combine(now.date(), end_time_obj)

        is_force_ended = self.history[self.today_str].get("force_ended", False)

        if is_force_ended or now >= d_end:
            m_txt, m_target = "День завершен!", now
            e_txt = "Рабочий день окончен! 🌸"
            diff = timedelta(seconds=0) 
        elif now < l_start:
            m_txt, m_target = "До обеда:", l_start
            e_txt = f"Конец дня в {'17:00' if now.weekday()==4 else '18:00'}"
            diff = m_target - now
        elif l_start <= now <= l_end:
            m_txt, m_target = "Обед еще:", l_end
            e_txt = "Приятного аппетита!"
            diff = m_target - now
        else:
            m_txt, m_target = "До конца дня:", d_end
            e_txt = "Обед завершен ✅"
            diff = m_target - now

        self.lbl_main_status.config(text=m_txt)
        self.lbl_main_time.config(text=self.fmt_delta(diff))
        self.lbl_extra.config(text=e_txt)
        
        worked = self.history[self.today_str]["worked_seconds"]
        self.lbl_stats.config(text=f"Отработано сегодня: {self.fmt_delta(timedelta(seconds=worked))}")

        bal = worked - daily_norm
        if bal >= 0:
            self.lbl_bal_title.config(text="🔥 ПЕРЕРАБОТКА:", fg="#e65100")
            self.lbl_bal_time.config(text=self.fmt_delta(timedelta(seconds=bal)), fg="#e65100")
        else:
            self.lbl_bal_title.config(text="⏳ ДОРАБОТАТЬ:", fg="#1565c0")
            self.lbl_bal_time.config(text=self.fmt_delta(timedelta(seconds=abs(bal))), fg="#1565c0")

        if not force_update:
            self.root.after(1000, self.update_loop)

    def fmt_delta(self, delta):
        s = int(max(0, delta.total_seconds()))
        return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

    def show_history_window(self):
        win = tk.Toplevel(self.root); win.title("Статистика"); win.geometry("360x400"); win.attributes("-topmost", True)
        nb = ttk.Notebook(win); nb.pack(fill="both", expand=True)
        
        f1 = tk.Frame(nb, bg="white"); nb.add(f1, text="Дни")
        t1 = ttk.Treeview(f1, columns=("d","s","t"), show="headings")
        for c, h in zip(("d","s","t"), ("Дата","Старт","Всего")): t1.heading(c, text=h); t1.column(c, width=100, anchor="center")
        t1.pack(fill="both", expand=True)
        for k in sorted(self.history.keys(), reverse=True):
            d = self.history[k]; s = int(d.get("worked_seconds",0))
            t1.insert("", 0, values=(k, d.get("start_time","-"), f"{s//3600}ч {s%3600//60:02d}м"))

        f2 = tk.Frame(nb, bg="white"); nb.add(f2, text="Месяцы")
        t2 = ttk.Treeview(f2, columns=("m","w","b"), show="headings")
        for c, h in zip(("m","w","b"), ("Месяц","Отработано","Баланс")): t2.heading(c, text=h); t2.column(c, width=110, anchor="center")
        t2.pack(fill="both", expand=True)
        
        m_data = {}
        for ds, data in self.history.items():
            mk = ds[:7]; y, m = mk.split('-')
            name = f"{MONTHS.get(m, m)} {y}"
            if name not in m_data: m_data[name] = {"w": 0, "n": 0}
            w_s = data.get("worked_seconds", 0)
            if w_s > 0:
                m_data[name]["w"] += w_s
                _, norm = self.get_day_config(datetime.strptime(ds, "%Y-%m-%d"))
                m_data[name]["n"] += norm
        
        for name in sorted(m_data.keys(), reverse=True):
            w, n = m_data[name]["w"], m_data[name]["n"]; b = w - n
            sign = "+" if b > 0 else "-" if b < 0 else ""
            t2.insert("", "end", values=(name, f"{int(w//3600)}ч", f"{sign}{int(abs(b)//3600)}ч {int(abs(b)%3600//60):02d}м"))

if __name__ == "__main__":
    app = MiniTimer(tk.Tk()); tk.mainloop()