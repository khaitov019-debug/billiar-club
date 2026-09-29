import os, sqlite3
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

def money(v):
    return f"{float(v):,.0f} so'm".replace(",", " ")

def timer_text(sec):
    sec = max(0, int(sec))
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

class DB:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS tables(
          id INTEGER PRIMARY KEY,kind TEXT,number INTEGER,price REAL DEFAULT 30000,
          active INTEGER DEFAULT 0,started TEXT,paused INTEGER DEFAULT 0,
          paused_at TEXT,paused_seconds INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,category TEXT,size TEXT,
          price REAL DEFAULT 0,cost REAL DEFAULT 0,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,table_number INTEGER,
          started TEXT,ended TEXT,seconds INTEGER,total REAL);
        CREATE TABLE IF NOT EXISTS sales(
          id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,table_number INTEGER,
          product_id INTEGER,name TEXT,category TEXT,size TEXT,qty INTEGER,
          total REAL,cost_total REAL,created TEXT);
        """)
        for k,v in {"club_name":"BILYARD CLUB","admin_password":""}.items():
            self.db.execute("INSERT OR IGNORE INTO settings VALUES(?,?)",(k,v))
        for i in range(1,6):
            self.db.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",(i,"BILLIARD",i,30000))
        for i in range(1,4):
            self.db.execute("INSERT OR IGNORE INTO tables(id,kind,number,price) VALUES(?,?,?,?)",(100+i,"TENNIS",i,20000))
        if self.db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            items=[
              ("Suv","Ichimlik","0.5L",3000),("Suv","Ichimlik","1L",5000),
              ("Suv","Ichimlik","1.5L",7000),("Suv","Ichimlik","2L",9000),
              ("Coca-Cola","Ichimlik","0.5L",7000),("Coca-Cola","Ichimlik","1L",11000),
              ("Fanta","Ichimlik","0.5L",7000),("Fanta","Ichimlik","1L",11000),
              ("Sprite","Ichimlik","0.5L",7000),("Sprite","Ichimlik","1L",11000),
              ("Pepsi","Ichimlik","0.5L",7000),("Pepsi","Ichimlik","1L",11000),
              ("Chips","Gazak","",10000),("Suxarik","Gazak","",8000),
              ("Shokolad","Gazak","",10000),("Yong'oq","Gazak","",15000),
              ("Pullik tayoqcha","Tayoqcha","",5000)]
            self.db.executemany("INSERT INTO products(name,category,size,price) VALUES(?,?,?,?)",items)
        self.db.commit()

    def now(self): return datetime.now()
    def setting(self,k):
        r=self.db.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
        return r["value"] if r else ""
    def elapsed(self,r):
        if not r["active"] or not r["started"]: return 0
        start=datetime.fromisoformat(r["started"])
        end=datetime.fromisoformat(r["paused_at"]) if r["paused"] and r["paused_at"] else self.now()
        return max(0,int((end-start).total_seconds())-int(r["paused_seconds"] or 0))
    def start(self,tid):
        self.db.execute("""UPDATE tables SET active=1,started=?,paused=0,
        paused_at=NULL,paused_seconds=0 WHERE id=?""",(self.now().isoformat(),tid))
        self.db.commit()
    def pause(self,tid):
        r=self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        if not r or not r["active"]: return
        now=self.now()
        if not r["paused"]:
            self.db.execute("UPDATE tables SET paused=1,paused_at=? WHERE id=?",(now.isoformat(),tid))
        else:
            extra=int((now-datetime.fromisoformat(r["paused_at"])).total_seconds()) if r["paused_at"] else 0
            self.db.execute("""UPDATE tables SET paused=0,paused_at=NULL,
            paused_seconds=paused_seconds+? WHERE id=?""",(max(0,extra),tid))
        self.db.commit()
    def finish(self,tid):
        r=self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        if not r or not r["active"]: return 0
        sec=self.elapsed(r); total=sec/3600*float(r["price"])
        self.db.execute("""INSERT INTO sessions(kind,table_number,started,ended,seconds,total)
        VALUES(?,?,?,?,?,?)""",(r["kind"],r["number"],r["started"],self.now().isoformat(),sec,total))
        self.db.execute("""UPDATE tables SET active=0,started=NULL,paused=0,
        paused_at=NULL,paused_seconds=0 WHERE id=?""",(tid,))
        self.db.commit(); return total
    def add_sale(self,tid,pid):
        t=self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        p=self.db.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
        if not t or not p or not t["active"]: return
        self.db.execute("""INSERT INTO sales(kind,table_number,product_id,name,category,size,qty,total,cost_total,created)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",(t["kind"],t["number"],p["id"],p["name"],p["category"],p["size"],1,p["price"],p["cost"] if "cost" in p.keys() else 0,self.now().isoformat()))
        self.db.commit()
    def sales(self,tid):
        t=self.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        if not t or not t["started"]: return []
        return self.db.execute("""SELECT name,size,SUM(qty) qty,SUM(total) total FROM sales
        WHERE kind=? AND table_number=? AND created>=? GROUP BY product_id ORDER BY name""",
        (t["kind"],t["number"],t["started"])).fetchall()

class Club(App):
    def build(self):
        self.db=DB(os.path.join(self.user_data_dir,"club_data.db"))
        Window.clearcolor=(.035,.067,.094,1)
        self.root=BoxLayout(orientation="vertical")
        self.cards={}
        self.home()
        Clock.schedule_interval(self.refresh,0.25)
        return self.root
    def lab(self,text,size=16,height=42):
        return Label(text=text,font_size=dp(size),size_hint_y=None,height=dp(height),color=(1,1,1,1))
    def btn(self,text,fn,height=44):
        b=Button(text=text,font_size=dp(15),size_hint_y=None,height=dp(height))
        b.bind(on_release=lambda *_:fn()); return b
    def home(self):
        self.root.clear_widgets(); self.cards={}
        h=BoxLayout(size_hint_y=None,height=dp(58),spacing=dp(5),padding=dp(5))
        h.add_widget(self.lab(self.db.setting("club_name"),20,48))
        h.add_widget(self.btn("🥤 MENYU",lambda:self.menu(),48))
        h.add_widget(self.btn("📊 HISOBOT",self.report,48))
        h.add_widget(self.btn("⚙ SOZLAMA",self.settings,48))
        self.root.add_widget(h)
        scroll=ScrollView(); grid=GridLayout(cols=1,spacing=dp(7),padding=dp(7),size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for r in self.db.db.execute("SELECT * FROM tables ORDER BY kind,number").fetchall():
            box=BoxLayout(orientation="vertical",size_hint_y=None,height=dp(128),padding=dp(6))
            box.add_widget(self.lab(f"{'🎱' if r['kind']=='BILLIARD' else '🏓'} {r['kind']} {r['number']}",17,30))
            t=self.lab(timer_text(self.db.elapsed(r)),25,34); s=self.lab(self.state(r),13,26)
            box.add_widget(t); box.add_widget(s)
            box.add_widget(self.btn("KIRISH / BOSHQARISH",lambda tid=r["id"]:self.table(tid),38))
            grid.add_widget(box); self.cards[r["id"]]=(t,s)
        scroll.add_widget(grid); self.root.add_widget(scroll)
    def state(self,r):
        return "⏸ PAUZA" if r["paused"] else ("🔴 BAND" if r["active"] else "🟢 BO'SH")
    def refresh(self,*_):
        rows={r["id"]:r for r in self.db.db.execute("SELECT * FROM tables")}
        for tid,(t,s) in self.cards.items():
            r=rows.get(tid)
            if r: t.text=timer_text(self.db.elapsed(r)); s.text=self.state(r)
    def popup(self,title):
        c=BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(7))
        return Popup(title=title,content=c,size_hint=(.94,.9)),c
    def table(self,tid):
        r=self.db.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
        p,c=self.popup(f"{r['kind']} {r['number']}")
        tm=self.lab(timer_text(self.db.elapsed(r)),32,52); st=self.lab(self.state(r),16,34)
        c.add_widget(tm);c.add_widget(st)
        row=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(4))
        if r["active"]:
            row.add_widget(self.btn("▶ DAVOM" if r["paused"] else "⏸ PAUZA",lambda:self.pause(tid,p),46))
            row.add_widget(self.btn("⏹ TUGATISH",lambda:self.finish(tid,p),46))
        else: row.add_widget(self.btn("▶ BAND QILISH",lambda:self.start(tid,p),46))
        row.add_widget(self.btn("🥤 MAHSULOT",lambda:self.menu(tid),46)); c.add_widget(row)
        sc=ScrollView(); sales=GridLayout(cols=1,size_hint_y=None);sales.bind(minimum_height=sales.setter("height"));sc.add_widget(sales);c.add_widget(sc)
        def tick(*_):
            if not p._window:return
            rr=self.db.db.execute("SELECT * FROM tables WHERE id=?",(tid,)).fetchone()
            tm.text=timer_text(self.db.elapsed(rr));st.text=self.state(rr);sales.clear_widgets()
            for x in self.db.sales(tid):sales.add_widget(self.lab(f"{x['name']} {x['size']} ×{x['qty']}   {money(x['total'])}",14,32))
            if rr["active"]:Clock.schedule_once(tick,.25)
        p.open();tick()
    def start(self,tid,p):
        self.db.start(tid);p.dismiss();self.table(tid)
    def pause(self,tid,p):
        self.db.pause(tid);p.dismiss();self.table(tid)
    def finish(self,tid,p):
        total=self.db.finish(tid);p.dismiss();self.home();self.info("Hisob",money(total))
    def menu(self,tid=None):
        p,c=self.popup("MAHSULOT QO'SHISH" if tid else "MENYU")
        sc=ScrollView();g=GridLayout(cols=1,size_hint_y=None,spacing=dp(5));g.bind(minimum_height=g.setter("height"))
        for x in self.db.db.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name").fetchall():
            size=f" ({x['size']})" if x["size"] else ""
            g.add_widget(self.btn(f"{x['name']}{size} — {money(x['price'])}",lambda pid=x["id"]:self.add(pid,tid,p),45) if tid else self.lab(f"{x['name']}{size} — {money(x['price'])}",15,40))
        sc.add_widget(g);c.add_widget(sc);p.open()
    def add(self,pid,tid,p):
        self.db.add_sale(tid,pid);p.dismiss();self.table(tid)
    def report(self):
        p,c=self.popup("HISOBOT");sc=ScrollView();g=GridLayout(cols=1,size_hint_y=None);g.bind(minimum_height=g.setter("height"))
        day=self.db.now().replace(hour=0,minute=0,second=0,microsecond=0).isoformat()
        ss=self.db.db.execute("SELECT * FROM sessions WHERE ended>=?",(day,)).fetchall()
        total=sum(float(x["total"]) for x in ss);sales=self.db.db.execute("SELECT SUM(total) total FROM sales WHERE created>=?",(day,)).fetchone()["total"] or 0
        g.add_widget(self.lab(f"STOLLAR: {money(total)}",17,40));g.add_widget(self.lab(f"MAHSULOTLAR: {money(sales)}",17,40));g.add_widget(self.lab(f"JAMI: {money(total+sales)}",20,45))
        sc.add_widget(g);c.add_widget(sc);p.open()
    def settings(self):
        p,c=self.popup("SOZLAMALAR")
        name=TextInput(text=self.db.setting("club_name"),multiline=False,size_hint_y=None,height=dp(45));c.add_widget(name)
        c.add_widget(self.btn("💾 SAQLASH",lambda:(self.db.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",("club_name",name.text)),self.db.db.commit(),p.dismiss(),self.home()),48))
        p.open()
    def info(self,title,msg):
        p,c=self.popup(title);c.add_widget(self.lab(msg,18,70));c.add_widget(self.btn("OK",p.dismiss,45));p.open()

if __name__=="__main__":
    Club().run()
