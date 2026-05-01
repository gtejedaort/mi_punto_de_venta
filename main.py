import sqlite3
import os
import datetime
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.label import MDLabel
from kivymd.uix.list import TwoLineAvatarIconListItem, IconRightWidget, OneLineListItem, ThreeLineListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu

# --- CONFIGURACIÓN DE RUTA ---
def obtener_ruta_db():
    nombre_db = "punto_venta_v8.db"
    if platform == 'android':
        from android.storage import app_storage_path
        return os.path.join(app_storage_path(), nombre_db)
    return nombre_db

# ==========================================================
# 1. LÓGICA DE BASE DE DATOS
# ==========================================================
def inicializar_db():
    conexion = sqlite3.connect(obtener_ruta_db())
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE, nombre TEXT NOT NULL, 
        costo REAL NOT NULL, precio REAL NOT NULL, stock INTEGER NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cedula_rnc TEXT UNIQUE, nombre TEXT NOT NULL, contacto TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial_ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total REAL NOT NULL, tipo TEXT, cliente_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS detalle_ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, venta_id INTEGER, 
        producto_nombre TEXT, cantidad INTEGER, costo_unitario REAL, precio_unitario REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        concepto TEXT NOT NULL, monto REAL NOT NULL)''')
    conexion.commit()
    conexion.close()

# ==========================================================
# 2. DEFINICIÓN DE PANTALLAS
# ==========================================================

class VentasScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total = 0.0
        self.tipo_pago = "Contado"
        self.menu_prod = None
        self.menu_cli = None

        layout = MDBoxLayout(orientation='vertical')
        layout.add_widget(MDTopAppBar(
            title="Punto de Venta",
            right_action_items=[
                ["account-plus", lambda x: self.ir_a("clientes")],
                ["cash-minus", lambda x: self.ir_a("gastos")],
                ["finance", lambda x: self.ir_a("utilidad")],
                ["file-document", lambda x: self.ir_a("reporte_total")],
                ["format-list-bulleted", lambda x: self.ir_a("lista_productos")], # BOTÓN PARA VER LISTADO
                ["archive-plus", lambda x: self.ir_a("inventario")],
            ]
        ))

        self.label_total = MDLabel(text="TOTAL: $0.00", halign="center", font_style="H3", size_hint_y=None, height="70dp")
        layout.add_widget(self.label_total)

        self.btn_pago = MDRaisedButton(text="MODO: CONTADO", md_bg_color="blue", on_release=self.cambiar_modo_pago, pos_hint={"center_x": .5})
        layout.add_widget(self.btn_pago)

        self.in_cli = MDTextField(hint_text="Cliente (ID o Nombre)")
        self.in_cli.bind(text=self.predictivo_cliente)

        self.in_prod = MDTextField(hint_text="Producto...")
        self.in_prod.bind(text=self.predictivo_producto)

        self.in_cant = MDTextField(hint_text="Cant", text="1", size_hint_x=0.2, input_filter="int")

        layout.add_widget(MDBoxLayout(self.in_cli, padding=[20, 5], adaptive_height=True))
        box_prod = MDBoxLayout(padding=[20, 5], spacing=10, adaptive_height=True)
        box_prod.add_widget(self.in_prod); box_prod.add_widget(self.in_cant)
        layout.add_widget(box_prod)

        self.lista = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=10)
        scroll = ScrollView(); scroll.add_widget(self.lista)
        layout.add_widget(scroll)

        layout.add_widget(MDRaisedButton(text="COBRAR", pos_hint={"center_x": .5}, on_release=self.finalizar, md_bg_color="green"))
        self.add_widget(layout)

    def ir_a(self, p): self.manager.current = p
    def cambiar_modo_pago(self, instance):
        self.tipo_pago = "Crédito" if self.tipo_pago == "Contado" else "Contado"
        instance.text = f"MODO: {self.tipo_pago.upper()}"
        instance.md_bg_color = "orange" if self.tipo_pago == "Crédito" else "blue"

    def predictivo_cliente(self, instance, value):
        if len(value) < 2: return
        conexion = sqlite3.connect(obtener_ruta_db()); cursor = conexion.cursor()
        cursor.execute("SELECT cedula_rnc, nombre FROM clientes WHERE nombre LIKE ?", (f'%{value}%',))
        datos = cursor.fetchall(); conexion.close()
        items = [{"viewclass": "OneLineListItem", "text": f"{c[1]} ({c[0]})", "on_release": lambda x=c: self.set_cli(x)} for c in datos]
        if self.menu_cli: self.menu_cli.dismiss()
        self.menu_cli = MDDropdownMenu(caller=self.in_cli, items=items, width_mult=4); self.menu_cli.open()

    def set_cli(self, c): self.in_cli.text = c[0]; self.menu_cli.dismiss()

    def predictivo_producto(self, instance, value):
        if len(value) < 1: return
        conexion = sqlite3.connect(obtener_ruta_db()); cursor = conexion.cursor()
        cursor.execute("SELECT nombre, precio FROM productos WHERE nombre LIKE ?", (f'%{value}%',))
        datos = cursor.fetchall(); conexion.close()
        items = [{"viewclass": "OneLineListItem", "text": f"{p[0]} - ${p[1]}", "on_release": lambda x=p: self.add_prod(x)} for p in datos]
        if self.menu_prod: self.menu_prod.dismiss()
        self.menu_prod = MDDropdownMenu(caller=self.in_prod, items=items, width_mult=4); self.menu_prod.open()

    def add_prod(self, p):
        self.menu_prod.dismiss()
        cant = int(self.in_cant.text) if self.in_cant.text else 1
        sub = p[1] * cant
        item = TwoLineAvatarIconListItem(text=f"{p[0]} (x{cant})", secondary_text=f"Sub: ${sub:.2f}")
        item.add_widget(IconRightWidget(icon="delete", on_release=lambda x: self.del_item(item, sub)))
        self.lista.add_widget(item); self.total += sub
        self.label_total.text = f"TOTAL: ${self.total:.2f}"; self.in_prod.text = ""

    def del_item(self, item, monto):
        self.lista.remove_widget(item); self.total -= monto
        self.label_total.text = f"TOTAL: ${max(0, self.total):.2f}"

    def finalizar(self, x):
        if self.total <= 0: return
        conexion = sqlite3.connect(obtener_ruta_db()); cursor = conexion.cursor()
        cursor.execute("INSERT INTO historial_ventas (total, tipo, cliente_id) VALUES (?, ?, ?)", (self.total, self.tipo_pago, self.in_cli.text))
        v_id = cursor.lastrowid
        for c in self.lista.children:
            p_nom = c.text.split(" (x")[0]
            p_can = int(c.text.split(" (x")[1].replace(")", ""))
            cursor.execute("SELECT costo, precio FROM productos WHERE nombre = ?", (p_nom,))
            pd = cursor.fetchone()
            cursor.execute("INSERT INTO detalle_ventas (venta_id, producto_nombre, cantidad, costo_unitario, precio_unitario) VALUES (?,?,?,?,?)", (v_id, p_nom, p_can, pd[0], pd[1]))
            cursor.execute("UPDATE productos SET stock = stock - ? WHERE nombre = ?", (p_can, p_nom))
        conexion.commit(); conexion.close()
        MDDialog(title="Éxito", text="Venta guardada").open()
        self.lista.clear_widgets(); self.total = 0; self.label_total.text = "TOTAL: $0.00"; self.in_cli.text = ""

class ListaProductosScreen(MDScreen):
    def on_enter(self):
        self.lista_items.clear_widgets()
        conexion = sqlite3.connect(obtener_ruta_db())
        res = conexion.execute("SELECT nombre, stock, precio FROM productos").fetchall()
        conexion.close()
        for p in res:
            self.lista_items.add_widget(
                OneLineListItem(text=f"{p[0]} | Stock: {p[1]} | Precio: ${p[2]:.2f}")
            )

    def __init__(self, **kw):
        super().__init__(**kw)
        l = MDBoxLayout(orientation='vertical')
        l.add_widget(MDTopAppBar(title="Inventario Actual", left_action_items=[["arrow-left", lambda x: setattr(self.manager, 'current', 'ventas')]]))
        self.lista_items = MDBoxLayout(orientation='vertical', adaptive_height=True)
        s = ScrollView(); s.add_widget(self.lista_items); l.add_widget(s)
        self.add_widget(l)

class ReporteTotalVentasScreen(MDScreen):
    def on_enter(self): self.cargar_ventas()
    def __init__(self, **kw):
        super().__init__(**kw)
        l = MDBoxLayout(orientation='vertical')
        l.add_widget(MDTopAppBar(title="Historial de Ventas", left_action_items=[["arrow-left", lambda x: setattr(self.manager, 'current', 'ventas')]]))
        self.container = MDBoxLayout(orientation='vertical', adaptive_height=True)
        scroll = ScrollView(); scroll.add_widget(self.container); l.add_widget(scroll)
        self.add_widget(l)

    def cargar_ventas(self):
        self.container.clear_widgets()
        conexion = sqlite3.connect(obtener_ruta_db()); cursor = conexion.cursor()
        cursor.execute("SELECT id, fecha, total, tipo, cliente_id FROM historial_ventas ORDER BY fecha DESC")
        ventas = cursor.fetchall(); conexion.close()
        for v in ventas:
            self.container.add_widget(ThreeLineListItem(text=f"Venta #{v[0]} - Total: ${v[2]:.2f}", secondary_text=f"Fecha: {v[1]} | Pago: {v[3]}", tertiary_text=f"Cliente ID: {v[4] if v[4] else 'General'}"))

class UtilidadScreen(MDScreen):
    def on_enter(self): self.actualizar()
    def __init__(self, **kw):
        super().__init__(**kw)
        l = MDBoxLayout(orientation='vertical')
        l.add_widget(MDTopAppBar(title="Utilidad Detallada", left_action_items=[["arrow-left", lambda x: setattr(self.manager, 'current', 'ventas')]]))
        self.res = MDLabel(text="", halign="center", adaptive_height=True, padding=[0, 10])
        l.add_widget(self.res)
        self.cont = MDBoxLayout(orientation='vertical', adaptive_height=True)
        s = ScrollView(); s.add_widget(self.cont); l.add_widget(s)
        self.add_widget(l)

    def actualizar(self):
        self.cont.clear_widgets()
        hoy = datetime.date.today().strftime("%Y-%m-%d")
        conexion = sqlite3.connect(obtener_ruta_db()); cursor = conexion.cursor()
        cursor.execute("SELECT producto_nombre, SUM(cantidad), SUM((precio_unitario - costo_unitario) * cantidad) FROM detalle_ventas d JOIN historial_ventas h ON d.venta_id = h.id WHERE h.fecha LIKE ? GROUP BY producto_nombre", (f'{hoy}%',))
        items = cursor.fetchall(); ganancia = 0
        for i in items:
            self.cont.add_widget(ThreeLineListItem(text=f"Producto: {i[0]}", secondary_text=f"Vendidos: {i[1]}", tertiary_text=f"Ganancia: ${i[2]:.2f}"))
            ganancia += i[2]
        cursor.execute("SELECT SUM(monto) FROM gastos WHERE fecha LIKE ?", (f'{hoy}%',))
        gas = cursor.fetchone()[0] or 0
        conexion.close()
        self.res.text = f"Ganancia Bruta: ${ganancia:.2f} | Gastos: ${gas:.2f}\nUTILIDAD NETA: ${ganancia - gas:.2f}"

class InventarioScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        l = MDBoxLayout(orientation='vertical')
        l.add_widget(MDTopAppBar(title="Agregar Producto", left_action_items=[["arrow-left", lambda x: setattr(self.manager, 'current', 'ventas')]]))
        f = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        self.c, self.n, self.co, self.p, self.s = MDTextField(hint_text="Código"), MDTextField(hint_text="Nombre"), MDTextField(hint_text="Costo", input_filter="float"), MDTextField(hint_text="Precio", input_filter="float"), MDTextField(hint_text="Stock", input_filter="int")
        for i in [self.c, self.n, self.co, self.p, self.s]: f.add_widget(i)
        f.add_widget(MDRaisedButton(text="GUARDAR", on_release=self.guardar, pos_hint={"center_x": .5}))
        l.add_widget(f); self.add_widget(l)
    def guardar(self, x):
        conexion = sqlite3.connect(obtener_ruta_db())
        try:
            conexion.execute("INSERT INTO productos (codigo_barras, nombre, costo, precio, stock) VALUES (?,?,?,?,?)", (self.c.text, self.n.text, float(self.co.text), float(self.p.text), int(self.s.text)))
            conexion.commit(); MDDialog(title="OK", text="Guardado").open()
            self.c.text = ""; self.n.text = ""; self.co.text = ""; self.p.text = ""; self.s.text = ""
        except: MDDialog(title="Error", text="Falla en registro").open()
        finally: conexion.close()

class ClientesScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        l = MDBoxLayout(orientation='vertical')
        l.add_widget(MDTopAppBar(title="Clientes", left_action_items=[["arrow-left", lambda x: setattr(self.manager, 'current', 'ventas')]]))
        f = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        self.in_id, self.nom, self.con = MDTextField(hint_text="ID"), MDTextField(hint_text="Nombre"), MDTextField(hint_text="Contacto")
        f.add_widget(self.in_id); f.add_widget(self.nom); f.add_widget(self.con)
        f.add_widget(MDRaisedButton(text="GUARDAR", on_release=self.save, pos_hint={"center_x": .5}))
        l.add_widget(f); self.add_widget(l)
    def save(self, x):
        conexion = sqlite3.connect(obtener_ruta_db())
        try:
            conexion.execute("INSERT INTO clientes (cedula_rnc, nombre, contacto) VALUES (?,?,?)", (self.in_id.text, self.nom.text, self.con.text))
            conexion.commit(); MDDialog(title="OK", text="Cliente Guardado").open()
            self.in_id.text = ""; self.nom.text = ""; self.con.text = ""
        except: MDDialog(title="Error", text="ID ya existe").open()
        finally: conexion.close()

class GastosScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        l = MDBoxLayout(orientation='vertical')
        l.add_widget(MDTopAppBar(title="Gastos", left_action_items=[["arrow-left", lambda x: setattr(self.manager, 'current', 'ventas')]]))
        f = MDBoxLayout(orientation='vertical', spacing=15, padding=25)
        self.c, self.m = MDTextField(hint_text="Concepto"), MDTextField(hint_text="Monto", input_filter="float")
        f.add_widget(self.c); f.add_widget(self.m)
        f.add_widget(MDRaisedButton(text="GUARDAR", on_release=self.save, pos_hint={"center_x": .5}))
        l.add_widget(f); self.add_widget(l)
    def save(self, x):
        conexion = sqlite3.connect(obtener_ruta_db())
        conexion.execute("INSERT INTO gastos (concepto, monto) VALUES (?,?)", (self.c.text, float(self.m.text)))
        conexion.commit(); conexion.close(); MDDialog(title="OK", text="Gasto Registrado").open()
        self.c.text = ""; self.m.text = ""

# ==========================================================
# 3. APP PRINCIPAL
# ==========================================================
class POSApp(MDApp):
    def build(self):
        inicializar_db()
        self.theme_cls.primary_palette = "Indigo"
        sm = ScreenManager()
        sm.add_widget(VentasScreen(name='ventas'))
        sm.add_widget(InventarioScreen(name='inventario'))
        sm.add_widget(ClientesScreen(name='clientes'))
        sm.add_widget(GastosScreen(name='gastos'))
        sm.add_widget(UtilidadScreen(name='utilidad'))
        sm.add_widget(ReporteTotalVentasScreen(name='reporte_total'))
        sm.add_widget(ListaProductosScreen(name='lista_productos'))
        return sm

if __name__ == "__main__":
    POSApp().run()