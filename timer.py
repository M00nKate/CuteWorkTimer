import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import json
import os
from datetime import datetime, time, timedelta

HISTORY_FILE = os.path.join(os.path.expanduser("~"), "timer_history.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), "timer_settings.json")

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
        
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#e8f5e9")
        
        self.settings = self.load_settings()
        self.history = self.load_history()
        self.today_str = datetime.now().strftime("%Y-%m-%d")
        self.check_today_exists()

        self.is_running = False
        self.is_lunching = False
        self.lunch_start_recorded = None
        self.lunch_end_recorded = None
        
        self.lunch_popup_shown = self.history[self.today_str].get("lunch_popup_shown", False)
        self.end_popup_shown = self.history[self.today_str].get("end_popup_shown", False)
        
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        self.setup_ui()
        self.last_tick = None
        self.update_loop()
        self.toggle_expand(force_collapse=True)

    def load_settings(self):
        default = {
            "work_start": "09:00",
            "work_end": "18:00",
            "work_end_fri": "17:00",
            "lunch_start": "13:00",
            "lunch_duration_mins": 40,
            "include_lunch_in_work": False
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: 
                    saved = json.load(f)
                    default.update(saved)
            except: pass
        return default

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f: json.dump(self.settings, f, indent=4)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f: return json.load(f)
            except: pass
        return {}

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w") as f: json.dump(self.history, f, indent=4)
        except: pass

    def check_today_exists(self):
        if self.today_str not in self.history:
            self.history[self.today_str] = {
                "start_time": None, 
                "worked_seconds": 0, 
                "force_ended": False,
                "lunch_popup_shown": False,
                "end_popup_shown": False,
                "lunch_taken": False
            }

    def setup_ui(self):
        self.top_frame = tk.Frame(self.root, bg="#e8f5e9")
        self.top_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Button(self.top_frame, text="✕", command=self.root.destroy, bg="#e8f5e9", borderwidth=0, fg="gray").pack(side="right")
        self.btn_expand = tk.Button(self.top_frame, text="▼", command=self.toggle_expand, bg="#e8f5e9", borderwidth=0)
        self.btn_expand.pack(side="right")
        
        tk.Button(self.top_frame, text="☰", command=self.show_history_window, bg="#e8f5e9", borderwidth=0, font=("Arial", 11)).pack(side="left", padx=(0, 2))
        tk.Button(self.top_frame, text="⚙️", command=self.open_settings, bg="#e8f5e9", borderwidth=0, font=("Arial", 11)).pack(side="left", padx=(0, 2))
        
        self.lbl_mini_timer = tk.Label(self.top_frame, text="--:--:--", bg="#e8f5e9", font=("Courier", 10, "bold"), fg="#333")
        self.lbl_mini_timer.pack(side="left", fill="x", expand=True)

        self.extra_frame = tk.Frame(self.root, bg="#e8f5e9")
        
        self.lbl_main_status = tk.Label(self.extra_frame, text="Ожидание...", bg="#e8f5e9", font=("Arial", 9))
        self.lbl_main_status.pack(pady=(5,0))
        self.lbl_main_time = tk.Label(self.extra_frame, text="00:00:00", bg="#e8f5e9", font=("Courier", 16, "bold"))
        self.lbl_main_time.pack()
        
        ttk.Separator(self.extra_frame, orient='horizontal').pack(fill='x', pady=5)
        self.lbl_extra = tk.Label(self.extra_frame, text="", bg="#e8f5e9", font=("Arial", 9))
        self.lbl_extra.pack()
        
        # Новый блок управления (кнопки)
        self.frame_controls = tk.Frame(self.extra_frame, bg="#e8f5e9")
        self.frame_controls.pack(pady=5)
        
        self.btn_start = tk.Button(self.frame_controls, text="▶ Начать", command=self.start_timer, bg="#a5d6a7", relief="flat", width=18)
        self.btn_pause = tk.Button(self.frame_controls, text="⏸ Пауза", command=self.pause_timer, bg="#fff9c4", relief="flat", width=8)
        self.btn_stop = tk.Button(self.frame_controls, text="⏹ Стоп", command=self.manual_end_day, bg="#ef9a9a", relief="flat", width=8)

        self.lbl_stats = tk.Label(self.extra_frame, text="Отработано: 00:00:00", bg="#e8f5e9", font=("Arial", 9, "italic"))
        self.lbl_stats.pack(pady=5)
        
        self.update_control_buttons()

    def update_control_buttons(self):
        self.btn_start.pack_forget()
        self.btn_pause.pack_forget()
        self.btn_stop.pack_forget()
        
        if self.history[self.today_str].get("force_ended", False):
            self.btn_start.config(text="▶ Начать заново")
            self.btn_start.pack(pady=2)
        elif not self.is_running:
            txt = "▶ Продолжить" if self.history[self.today_str].get("start_time") else "▶ Начать"
            self.btn_start.config(text=txt)
            self.btn_start.pack(pady=2)
        else:
            self.btn_pause.pack(side="left", padx=5)
            self.btn_stop.pack(side="left", padx=5)
            
        if self.is_expanded:
            self.root.update_idletasks()
            self.root.geometry(f"240x{self.root.winfo_reqheight()}")

    def start_move(self, event): self.x, self.y = event.x, event.y
    def do_move(self, event):
        x, y = self.root.winfo_x() + (event.x - self.x), self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def toggle_expand(self, force_collapse=False):
        if force_collapse: self.is_expanded = True
        
        self.is_expanded = not self.is_expanded
        if not self.is_expanded:
            self.extra_frame.pack_forget()
            self.lbl_mini_timer.pack(side="left", fill="x", expand=True)
            self.btn_expand.config(text="▼")
            self.root.geometry("240x28")
        else:
            self.lbl_mini_timer.pack_forget()
            self.extra_frame.pack(fill="both", expand=True)
            self.btn_expand.config(text="▲")
            self.root.update_idletasks()
            self.root.geometry(f"240x{self.root.winfo_reqheight()}")

    def start_timer(self):
        if self.history[self.today_str].get("force_ended", False):
            self.history[self.today_str]["force_ended"] = False
        self.is_running = True
        if not self.history[self.today_str].get("start_time"):
            self.history[self.today_str]["start_time"] = datetime.now().strftime("%H:%M")
        self.last_tick = datetime.now()
        self.update_control_buttons()

    def pause_timer(self):
        self.is_running = False
        self.save_history()
        self.update_control_buttons()
        self.update_loop(force_update=True)

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Настройки")
        win.geometry("280x360")
        win.attributes("-topmost", True)
        
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Вкладка 1: Рабочее время
        f_time = tk.Frame(nb, bg="white")
        nb.add(f_time, text="График")
        
        ttk.Label(f_time, text="Начало (ЧЧ:ММ):").pack(pady=(10,0))
        e_ws = ttk.Entry(f_time, justify="center"); e_ws.insert(0, self.settings["work_start"]); e_ws.pack()
        ttk.Label(f_time, text="Конец ПН-ЧТ (ЧЧ:ММ):").pack(pady=(5,0))
        e_we = ttk.Entry(f_time, justify="center"); e_we.insert(0, self.settings["work_end"]); e_we.pack()
        ttk.Label(f_time, text="Конец ПТ (ЧЧ:ММ):").pack(pady=(5,0))
        e_wef = ttk.Entry(f_time, justify="center"); e_wef.insert(0, self.settings["work_end_fri"]); e_wef.pack()
        ttk.Label(f_time, text="Обед (ЧЧ:ММ):").pack(pady=(5,0))
        e_ls = ttk.Entry(f_time, justify="center"); e_ls.insert(0, self.settings["lunch_start"]); e_ls.pack()
        ttk.Label(f_time, text="Длительность (мин):").pack(pady=(5,0))
        e_ld = ttk.Entry(f_time, justify="center"); e_ld.insert(0, str(self.settings["lunch_duration_mins"])); e_ld.pack()

        var_inc_lunch = tk.BooleanVar(value=self.settings.get("include_lunch_in_work", False))
        tk.Checkbutton(f_time, text="Обед входит в раб. время", variable=var_inc_lunch, bg="white").pack(pady=5)

        def save_settings_tab():
            self.settings["work_start"] = e_ws.get()
            self.settings["work_end"] = e_we.get()
            self.settings["work_end_fri"] = e_wef.get()
            self.settings["lunch_start"] = e_ls.get()
            self.settings["lunch_duration_mins"] = int(e_ld.get())
            self.settings["include_lunch_in_work"] = var_inc_lunch.get()
            self.save_settings()
            self.update_loop(force_update=True)
            messagebox.showinfo("Сохранено", "Настройки сохранены!", parent=win)

        tk.Button(f_time, text="Сохранить", command=save_settings_tab, bg="#a5d6a7", relief="flat").pack(pady=10)

        # Вкладка 2: Указать старт
        f_start = tk.Frame(nb, bg="white")
        nb.add(f_start, text="Старт")
        tk.Label(f_start, text="Во сколько вы начали работать?\n(Например: 09:00)", bg="white").pack(pady=15)
        e_start_time = ttk.Entry(f_start, justify="center", font=("Courier", 14))
        e_start_time.pack(pady=5)
        
        def apply_start_time():
            t = e_start_time.get()
            try:
                h, m = map(int, t.replace(".", ":").split(':'))
                now = datetime.now()
                start = now.replace(hour=h, minute=m, second=0)
                worked = (now - start).total_seconds()
                ls_time = datetime.strptime(self.settings["lunch_start"], "%H:%M").time()
                l_s = datetime.combine(now.date(), ls_time)
                l_dur = timedelta(minutes=self.settings["lunch_duration_mins"])
                if not self.settings.get("include_lunch_in_work", False):
                    if start < l_s and now > (l_s + l_dur): worked -= l_dur.total_seconds()
                self.history[self.today_str]["worked_seconds"] = max(0, worked)
                self.history[self.today_str]["start_time"] = f"{h:02d}:{m:02d}"
                self.history[self.today_str]["force_ended"] = False
                if not self.is_running: self.start_timer()
                else: self.last_tick = now 
                self.save_history()
                self.update_control_buttons()
                self.update_loop(force_update=True)
                messagebox.showinfo("Готово", "Время старта обновлено!", parent=win)
            except: messagebox.showerror("Ошибка", "Неверный формат (ЧЧ:ММ)", parent=win)

        tk.Button(f_start, text="Применить", command=apply_start_time, bg="#fff9c4", relief="flat").pack(pady=15)

        # Вкладка 3: Корректировка
        f_adj = tk.Frame(nb, bg="white")
        nb.add(f_adj, text="Корректировка")
        tk.Label(f_adj, text="Добавить или убавить время:", bg="white").pack(pady=15)
        
        f_spins = tk.Frame(f_adj, bg="white"); f_spins.pack()
        tk.Label(f_spins, text="Часы:").grid(row=0, column=0, pady=5)
        spin_h = ttk.Spinbox(f_spins, from_=-12, to=12, width=5); spin_h.set(0); spin_h.grid(row=0, column=1, padx=5)
        tk.Label(f_spins, text="Минуты:").grid(row=1, column=0, pady=5)
        spin_m = ttk.Spinbox(f_spins, from_=-59, to=59, width=5); spin_m.set(0); spin_m.grid(row=1, column=1, padx=5)

        def apply_adjust():
            total_sec = (int(spin_h.get()) * 3600) + (int(spin_m.get()) * 60)
            self.history[self.today_str]["worked_seconds"] += total_sec
            if self.history[self.today_str]["worked_seconds"] < 0: self.history[self.today_str]["worked_seconds"] = 0
            self.save_history()
            self.update_loop(force_update=True)
            messagebox.showinfo("Готово", "Время откорректировано!", parent=win)
            spin_h.set(0); spin_m.set(0)

        tk.Button(f_adj, text="Применить", command=apply_adjust, bg="#e1bee7", relief="flat").pack(pady=20)
        
    def check_events(self, now, l_start, l_end, d_end):
        if not self.lunch_popup_shown and now >= l_start and now < l_end and not self.history[self.today_str].get("force_ended"):
            self.lunch_popup_shown = True
            self.history[self.today_str]["lunch_popup_shown"] = True
            self.save_history()
            self.show_lunch_popup()
            
        if not self.end_popup_shown and now >= d_end and not self.history[self.today_str].get("force_ended"):
            self.end_popup_shown = True
            self.history[self.today_str]["end_popup_shown"] = True
            self.save_history()
            self.show_end_popup()

    def show_lunch_popup(self):
        win = tk.Toplevel(self.root)
        win.title("Время обеда!")
        win.geometry("300x150")
        win.attributes("-topmost", True)
        win.update_idletasks()
        win.geometry(f"+{(win.winfo_screenwidth() // 2) - 150}+{(win.winfo_screenheight() // 2) - 75}")

        tk.Label(win, text="🍲 Время обеда!", font=("Arial", 16, "bold")).pack(pady=15)
        f = tk.Frame(win); f.pack()
        
        def start_lunch():
            self.pause_timer()
            self.is_lunching = True
            self.lunch_start_recorded = datetime.now()
            self.history[self.today_str]["lunch_taken"] = True
            self.save_history()
            win.destroy()
            self.show_lunch_timer_window()

        tk.Button(f, text="Начать обед", command=start_lunch, bg="#a5d6a7", relief="flat", width=12).pack(side="left", padx=10)
        tk.Button(f, text="Пропустить", command=win.destroy, bg="#e0e0e0", relief="flat", width=12).pack(side="left", padx=10)

    def show_lunch_timer_window(self):
        l_win = tk.Toplevel(self.root)
        l_win.title("Обед")
        l_win.geometry("200x120+10+100")
        l_win.attributes("-topmost", True)
        l_win.configure(bg="#fff9c4")
        
        tk.Label(l_win, text="Обед идет:", bg="#fff9c4", font=("Arial", 10)).pack(pady=5)
        lbl_time = tk.Label(l_win, text="00:00", bg="#fff9c4", font=("Courier", 20, "bold"), fg="#f57f17")
        lbl_time.pack()

        def update_l_timer():
            if not self.is_lunching: return
            diff = datetime.now() - self.lunch_start_recorded
            lbl_time.config(text=self.fmt_delta(diff)[3:])
            l_win.after(1000, update_l_timer)
            
        def stop_lunch():
            self.is_lunching = False
            self.lunch_end_recorded = datetime.now()
            self.start_timer()
            l_win.destroy()

        tk.Button(l_win, text="Закончить обед", command=stop_lunch, bg="#ffcc80", relief="flat").pack(pady=10)
        update_l_timer()

    def show_end_popup(self):
        win = tk.Toplevel(self.root)
        win.title("Конец дня")
        win.geometry("350x180")
        win.attributes("-topmost", True)
        win.update_idletasks()
        win.geometry(f"+{(win.winfo_screenwidth()//2)-175}+{(win.winfo_screenheight()//2)-90}")

        tk.Label(win, text="🎉 Поздравляю!", font=("Arial", 14, "bold")).pack(pady=(15,5))
        tk.Label(win, text="Рабочий день по графику подошел к концу.\nЗавершить день или продолжить работу?").pack()
        f = tk.Frame(win); f.pack(pady=15)
        
        def finish(): win.destroy(); self.manual_end_day()
        tk.Button(f, text="Завершить", command=finish, bg="#ffcdd2", fg="#c62828", font=("Arial", 10, "bold"), relief="flat").pack(side="left", padx=10)
        tk.Button(f, text="Продолжить", command=win.destroy, bg="#a5d6a7", relief="flat").pack(side="left", padx=10)

    def manual_end_day(self):
        self.is_running = False 
        self.history[self.today_str]["force_ended"] = True
        self.save_history()
        self.update_control_buttons()
        self.update_loop(force_update=True)
        self.show_summary_window()

    def show_summary_window(self):
        win = tk.Toplevel(self.root)
        win.title("Итоги дня")
        win.geometry("300x250")
        win.attributes("-topmost", True)
        win.configure(bg="white")
        win.update_idletasks()
        win.geometry(f"+{(win.winfo_screenwidth()//2)-150}+{(win.winfo_screenheight()//2)-125}")

        worked = self.history[self.today_str].get("worked_seconds", 0)
        _, norm = self.get_day_config(datetime.now())
        bal = worked - norm

        tk.Label(win, text="📊 Итоги за сегодня", font=("Arial", 14, "bold"), bg="white").pack(pady=15)
        tk.Label(win, text=f"Отработано: {self.fmt_delta(timedelta(seconds=worked))}", font=("Arial", 11), bg="white").pack(pady=2)
        
        lunch_txt = "Обед: Был" if self.history[self.today_str].get("lunch_taken") else "Обед: Не зафиксирован"
        tk.Label(win, text=lunch_txt, font=("Arial", 10, "italic"), bg="white", fg="gray").pack(pady=2)

        bal_txt = f"Переработка: {self.fmt_delta(timedelta(seconds=bal))}" if bal >= 0 else f"Недоработка: {self.fmt_delta(timedelta(seconds=abs(bal)))}"
        bal_color = "#e65100" if bal >= 0 else "#1565c0"
        
        tk.Label(win, text=bal_txt, font=("Arial", 12, "bold"), fg=bal_color, bg="white").pack(pady=15)
        tk.Button(win, text="ОК", command=win.destroy, width=15, bg="#e0e0e0", relief="flat").pack()

    def get_day_config(self, dt):
        is_friday = dt.weekday() == 4
        start_t = datetime.strptime(self.settings["work_start"], "%H:%M")
        end_str = self.settings["work_end_fri"] if is_friday else self.settings["work_end"]
        end_t = datetime.strptime(end_str, "%H:%M")
        
        total_sec = (end_t - start_t).total_seconds()
        if not self.settings.get("include_lunch_in_work", False):
            total_sec -= (self.settings["lunch_duration_mins"] * 60)
            
        return end_t.time(), total_sec

    def update_loop(self, force_update=False):
        now = datetime.now()
        
        if self.is_running and self.last_tick:
            self.history[self.today_str]["worked_seconds"] += (now - self.last_tick).total_seconds()
            self.last_tick = now
            if int(now.timestamp()) % 10 == 0: self.save_history()

        end_time_obj, daily_norm = self.get_day_config(now)
        ls_time = datetime.strptime(self.settings["lunch_start"], "%H:%M").time()
        l_start = datetime.combine(now.date(), ls_time)
        l_end = l_start + timedelta(minutes=self.settings["lunch_duration_mins"])
        d_end = datetime.combine(now.date(), end_time_obj)

        self.check_events(now, l_start, l_end, d_end)

        is_force_ended = self.history.get(self.today_str, {}).get("force_ended", False)

        if is_force_ended or now >= d_end:
            m_txt, e_txt, diff = "День завершен!", "Рабочий день окончен! 🌸", timedelta(0)
        elif now < l_start:
            m_txt, e_txt, diff = "До обеда:", f"Конец в {end_time_obj.strftime('%H:%M')}", l_start - now
        elif l_start <= now <= l_end:
            m_txt, e_txt, diff = "Обед еще:", "Приятного аппетита!", l_end - now
        else:
            m_txt, e_txt, diff = "До конца дня:", "Обед завершен ✅", d_end - now

        timer_str = self.fmt_delta(diff)
        self.lbl_main_status.config(text=m_txt)
        self.lbl_main_time.config(text=timer_str)
        self.lbl_extra.config(text=e_txt)
        # Оставляем только таймер, без текстовой приписки (m_txt)
        self.lbl_mini_timer.config(text=timer_str)

        worked = self.history.get(self.today_str, {}).get("worked_seconds", 0)
        self.lbl_stats.config(text=f"Отработано сегодня: {self.fmt_delta(timedelta(seconds=worked))}")

        if not force_update: self.root.after(1000, self.update_loop)

    def fmt_delta(self, delta):
        s = int(max(0, delta.total_seconds()))
        return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

    def show_history_window(self):
        win = tk.Toplevel(self.root)
        win.title("Статистика и Управление")
        win.geometry("420x550") 
        win.attributes("-topmost", True)
        
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=5, pady=5)
        
        f1 = tk.Frame(nb, bg="white"); nb.add(f1, text="Дни")
        t1 = ttk.Treeview(f1, columns=("d","s","t"), show="headings", height=10)
        for c, h, w in zip(("d","s","t"), ("Дата","Старт","Отработано"), (110, 80, 110)): 
            t1.heading(c, text=h); t1.column(c, width=w, anchor="center")
        t1.pack(fill="both", expand=True, padx=5, pady=5)

        f1_btns = tk.Frame(f1, bg="white")
        f1_btns.pack(fill="x", padx=5, pady=5)

        f2 = tk.Frame(nb, bg="white"); nb.add(f2, text="Месяцы")
        lbl_total_bal = tk.Label(f2, text="", font=("Arial", 11, "bold"), bg="white", pady=5)
        lbl_total_bal.pack()
        t2 = ttk.Treeview(f2, columns=("m","w","b"), show="headings", height=10)
        for c, h, w in zip(("m","w","b"), ("Месяц","Отработано","Баланс"), (120, 90, 110)): 
            t2.heading(c, text=h); t2.column(c, width=w, anchor="center")
        t2.pack(fill="both", expand=True, padx=5, pady=5)

        f3 = tk.Frame(nb, bg="white"); nb.add(f3, text="График")
        
        top_f3 = tk.Frame(f3, bg="white")
        top_f3.pack(fill="x", padx=10, pady=5)
        tk.Label(top_f3, text="Месяц:", bg="white").pack(side="left")
        combo_var = tk.StringVar()
        combo = ttk.Combobox(top_f3, textvariable=combo_var, state="readonly", width=15)
        combo.pack(side="left", padx=5)

        canvas = tk.Canvas(f3, bg="white", height=200)
        canvas.pack(fill="both", expand=True, padx=10, pady=5)

        bot_f3 = tk.Frame(f3, bg="white")
        bot_f3.pack(fill="x", padx=10, pady=10)
        lbl_graph_tot = tk.Label(bot_f3, text="Отработано: 0ч 0м", bg="white", font=("Arial", 10))
        lbl_graph_tot.pack()
        lbl_graph_bal = tk.Label(bot_f3, text="Баланс: 0ч 0м", bg="white", font=("Arial", 10, "bold"))
        lbl_graph_bal.pack()

        def refresh_data():
            for item in t1.get_children(): t1.delete(item)
            for item in t2.get_children(): t2.delete(item)
            
            valid_months_map = {} 
            
            for k in sorted(self.history.keys(), reverse=True):
                s = int(self.history[k].get("worked_seconds", 0))
                t1.insert("", "end", values=(k, self.history[k].get("start_time","-"), f"{s//3600}ч {s%3600//60:02d}м"))
            
            m_data = {}
            total_historical_balance = 0
            
            for ds, data in self.history.items():
                w_s = data.get("worked_seconds", 0)
                if w_s > 0:
                    mk = ds[:7]; y, m = mk.split('-')
                    name = f"{MONTHS.get(m, m)} {y}"
                    
                    if name not in m_data: m_data[name] = {"w_all": 0, "w_bal": 0, "n": 0}
                    if name not in valid_months_map: valid_months_map[name] = mk
                    
                    m_data[name]["w_all"] += w_s
                    
                    # ИСПРАВЛЕНИЕ: И норма, И отработанное время идут в баланс ТОЛЬКО если день завершен
                    if ds != self.today_str or self.history[self.today_str].get("force_ended"):
                        dt_obj = datetime.strptime(ds, "%Y-%m-%d")
                        _, norm = self.get_day_config(dt_obj)
                        m_data[name]["w_bal"] += w_s
                        m_data[name]["n"] += norm
                        total_historical_balance += (w_s - norm)
            
            t_sign = "+" if total_historical_balance >= 0 else "-"
            t_color = "#e65100" if total_historical_balance >= 0 else "#1565c0"
            t_h = int(abs(total_historical_balance)) // 3600
            t_m = (int(abs(total_historical_balance)) % 3600) // 60
            lbl_total_bal.config(text=f"ИСТОРИЧЕСКИЙ БАЛАНС: {t_sign}{t_h}ч {t_m:02d}м", fg=t_color)

            for name in sorted(m_data.keys(), reverse=True):
                w_all = m_data[name]["w_all"]
                b = m_data[name]["w_bal"] - m_data[name]["n"]
                sign = "+" if b > 0 else "-" if b < 0 else ""
                t2.insert("", "end", values=(name, f"{int(w_all//3600)}ч", f"{sign}{int(abs(b)//3600)}ч {int(abs(b)%3600//60):02d}м"))

            combo['values'] = list(valid_months_map.keys())
            
            def update_graph(*args):
                sel_name = combo_var.get()
                if not sel_name or sel_name not in valid_months_map: return
                sel_ym = valid_months_map[sel_name]

                # Собираем даты, но пропускаем СЕГОДНЯ, если день еще не завершен (force_ended == False)
                dates = sorted([
                    d for d in self.history.keys() 
                    if d.startswith(sel_ym) 
                    and self.history[d].get("worked_seconds", 0) > 0
                    and (d != self.today_str or self.history[d].get("force_ended", False))
                ])

                tot_w_all = 0
                tot_w_bal = 0
                tot_n = 0
                for d in dates:
                    w = self.history[d].get("worked_seconds", 0)
                    tot_w_all += w
                    
                    # ИСПРАВЛЕНИЕ: И норма, И отработанное время идут в баланс ТОЛЬКО если день завершен
                    if d != self.today_str or self.history[self.today_str].get("force_ended"):
                        _, norm = self.get_day_config(datetime.strptime(d, "%Y-%m-%d"))
                        tot_w_bal += w
                        tot_n += norm

                th, tm = int(tot_w_all)//3600, (int(tot_w_all)%3600)//60
                lbl_graph_tot.config(text=f"Отработано всего: {th}ч {tm:02d}м")

                bal = tot_w_bal - tot_n
                sign = "+" if bal >= 0 else "-"
                bh, bm = int(abs(bal))//3600, (int(abs(bal))%3600)//60
                b_color = "#e65100" if bal >= 0 else "#1565c0"
                lbl_graph_bal.config(text=f"Баланс: {sign}{bh}ч {bm:02d}м", fg=b_color)

                canvas.delete("all")
                if not dates: return

                c_width, c_height = 360, 200
                max_h = max([self.history[d].get("worked_seconds", 0) for d in dates] + [9*3600]) 
                
                n_bars = len(dates)
                spacing = 5
                usable_width = c_width - 20
                bar_w = min(30, max(2, (usable_width - spacing*(n_bars-1)) / n_bars))
                
                total_content_w = n_bars * bar_w + (n_bars-1)*spacing
                start_x = (c_width - total_content_w) / 2 + 10

                for i, d in enumerate(dates):
                    w_sec = self.history[d].get("worked_seconds", 0)
                    h_px = (w_sec / max_h) * (c_height - 40) 
                    
                    x0 = start_x + i * (bar_w + spacing)
                    y0 = c_height - 20 - h_px
                    x1 = x0 + bar_w
                    y1 = c_height - 20
                    
                    color = "#a5d6a7"
                    if w_sec < 7.5 * 3600: color = "#90caf9"
                    elif w_sec > 8.5 * 3600: color = "#ffcc80"
                    
                    canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
                    if bar_w > 15:
                        canvas.create_text(x0 + bar_w/2, y0 - 10, text=f"{int(w_sec//3600)}ч", font=("Arial", 7))
                    canvas.create_text(x0 + bar_w/2, y1 + 10, text=d[-2:], font=("Arial", 7))

            combo.bind("<<ComboboxSelected>>", update_graph)
            if combo['values']:
                combo.current(0)
                update_graph()

        def open_editor():
            sel = t1.selection()
            def_date, def_start = self.today_str, "09:00"
            if sel:
                item = t1.item(sel[0])['values']
                def_date, def_start = item[0], item[1] if item[1] != "-" else "09:00"

            edit_win = tk.Toplevel(win)
            edit_win.title("Запись")
            edit_win.geometry("250x230")
            edit_win.attributes("-topmost", True)
            edit_win.configure(bg="white")

            tk.Label(edit_win, text="Дата (ГГГГ-ММ-ДД):", bg="white").pack(pady=(10,0))
            ent_date = tk.Entry(edit_win, justify="center"); ent_date.insert(0, def_date); ent_date.pack()

            tk.Label(edit_win, text="Начало (ЧЧ:ММ):", bg="white").pack(pady=(10,0))
            ent_start = tk.Entry(edit_win, justify="center"); ent_start.insert(0, def_start); ent_start.pack()

            tk.Label(edit_win, text="Конец (ЧЧ:ММ):", bg="white").pack(pady=(10,0))
            ent_end = tk.Entry(edit_win, justify="center"); ent_end.insert(0, "18:00"); ent_end.pack()

            def save_record():
                d_val, s_val, e_val = ent_date.get(), ent_start.get(), ent_end.get()
                
                try:
                    start_dt = datetime.strptime(f"{d_val} {s_val}", "%Y-%m-%d %H:%M")
                    end_dt = datetime.strptime(f"{d_val} {e_val}", "%Y-%m-%d %H:%M")
                    if end_dt <= start_dt:
                        messagebox.showerror("Ошибка", "Конец не может быть раньше начала!", parent=edit_win)
                        return
                    
                    worked = (end_dt - start_dt).total_seconds()
                    
                    ls_time = datetime.strptime(self.settings["lunch_start"], "%H:%M").time()
                    l_s = datetime.combine(start_dt.date(), ls_time)
                    l_dur = timedelta(minutes=self.settings["lunch_duration_mins"])
                    l_e = l_s + l_dur
                    
                    if not self.settings.get("include_lunch_in_work", False):
                        overlap_s = max(start_dt, l_s)
                        overlap_e = min(end_dt, l_e)
                        if overlap_e > overlap_s:
                            worked -= (overlap_e - overlap_s).total_seconds()

                    if d_val == self.today_str: self.pause_timer()

                    if d_val not in self.history: self.history[d_val] = {}
                    
                    self.history[d_val]["start_time"] = s_val
                    self.history[d_val]["worked_seconds"] = max(0, worked)
                    self.history[d_val]["force_ended"] = True 
                    
                    self.save_history()
                    refresh_data()
                    self.update_loop(force_update=True)
                    edit_win.destroy()
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверный формат. Используйте ГГГГ-ММ-ДД и ЧЧ:ММ", parent=edit_win)

            tk.Button(edit_win, text="💾 Сохранить запись", bg="#a5d6a7", relief="flat", command=save_record).pack(pady=15)

        def delete_record():
            sel = t1.selection()
            if not sel: return
            date_to_del = t1.item(sel[0])['values'][0]
            if messagebox.askyesno("Удаление", f"Удалить запись за {date_to_del}?", parent=win):
                if date_to_del in self.history: del self.history[date_to_del]
                if date_to_del == self.today_str:
                    self.pause_timer()
                    self.check_today_exists()
                self.save_history()
                refresh_data()
                self.update_loop(force_update=True)

        tk.Button(f1_btns, text="➕ Добавить/Изменить", command=open_editor, bg="#fff9c4", relief="flat", width=22).pack(side="left", padx=5)
        tk.Button(f1_btns, text="❌ Удалить", command=delete_record, bg="#ffcdd2", relief="flat", width=12).pack(side="right", padx=5)

        refresh_data()

if __name__ == "__main__":
    app = MiniTimer(tk.Tk())
    tk.mainloop()