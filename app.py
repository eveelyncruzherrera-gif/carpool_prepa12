from flask import Flask, request, redirect
import math

app = Flask(__name__)

PREPA_LAT = 25.5736644
PREPA_LON = -99.9894349

cuentas = {}
mensajes = {}
grupos = {}
online = set()

# 📏 DISTANCIA
def distancia(lat1, lon1, lat2, lon2):
    R = 6371

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)

    a = (math.sin(dLat/2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dLon/2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

def tiene_ubicacion(m):
    return m in cuentas and "casa" in cuentas[m]

def get_coords(m):
    return cuentas[m]["casa"]["lat"], cuentas[m]["casa"]["lon"]

def usuarios_cercanos(m, radio_km):
    cercanos = []

    if not tiene_ubicacion(m):
        return cercanos

    lat1, lon1 = get_coords(m)

    for u in cuentas:
        if u != m and tiene_ubicacion(u):
            lat2, lon2 = get_coords(u)
            if distancia(lat1, lon1, lat2, lon2) <= radio_km:
                cercanos.append(u)

    return cercanos

# 🔐 LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        m = request.form["matricula"]
        p = request.form["password"]

        if m in cuentas and cuentas[m]["password"] == p:
            online.add(m)
            return redirect(f"/home/{m}")
        else:
            return "<h3 style='text-align:center;color:red;'>❌ Error</h3>"

    return """
    <h1 style='text-align:center'>🔐 Login</h1>

    <form method="post" style="text-align:center">
    <input name="matricula" placeholder="📘 Matrícula"><br><br>
    <input name="password" type="password" placeholder="🔒 Contraseña"><br><br>
    <button>Entrar</button>
    </form>

    <div style="text-align:center">
    <a href="/registro">Crear cuenta</a>
    </div>
    """

# 🆕 REGISTRO
@app.route("/registro", methods=["GET","POST"])
def registro():
    if request.method == "POST":
        cuentas[request.form["matricula"]] = {
            "nombre": request.form["nombre"],
            "password": request.form["password"]
        }
        return redirect("/")

    return """
    <h1 style='text-align:center'>Registro</h1>

    <form method="post" style="text-align:center">
    <input name="nombre" placeholder="Nombre"><br><br>
    <input name="matricula" placeholder="Matrícula"><br><br>
    <input name="password" type="password" placeholder="Contraseña"><br><br>
    <button>Registrar</button>
    </form>
    """

# 🏠 HOME
@app.route("/home/<m>")
def home(m):

    return f"""
    <h2 style='text-align:center'>Bienvenido {cuentas[m]['nombre']}</h2>

    <div id="map" style="height:400px;"></div>

    <button onclick="guardarUbicacion()" style="display:block;margin:auto;">
    💾 Guardar mi casa
    </button>

    <p id="status" style="text-align:center;color:green;"></p>

    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

    <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.css"/>
    <script src="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.js"></script>

    <script>
    let casa = null;

    var map = L.map('map').setView([{PREPA_LAT},{PREPA_LON}], 15);

    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

    L.marker([{PREPA_LAT},{PREPA_LON}]).addTo(map).bindPopup("Prepa");

    map.on('click', function(e) {{

        casa = e.latlng;

        L.marker(casa).addTo(map).bindPopup("Tu casa").openPopup();

        L.Routing.control({{
            waypoints: [
                L.latLng(casa.lat, casa.lng),
                L.latLng({PREPA_LAT},{PREPA_LON})
            ],
            language: 'es',
            addWaypoints:false
        }}).addTo(map);
    }});

    function guardarUbicacion() {{
        if (!casa) {{
            alert("Primero selecciona tu casa");
            return;
        }}

        fetch(`/guardar_ubicacion/{m}/${{casa.lat}}/${{casa.lng}}`)
        .then(() => {{
            document.getElementById("status").innerHTML = "✅ Ubicación guardada";
        }});
    }}
    </script>

    <br>
    <div style="text-align:center">
    <a href="/carpool/{m}">🚗 Carpool</a><br><br>
    <a href="/chats/{m}">💬 Chats</a>
    </div>
    """

# 💾 GUARDAR
@app.route("/guardar_ubicacion/<m>/<lat>/<lon>")
def guardar(m, lat, lon):
    cuentas[m]["casa"] = {"lat": float(lat), "lon": float(lon)}
    return "ok"

# 🚗 CARPOOL
@app.route("/carpool/<m>")
def carpool(m):

    if not tiene_ubicacion(m):
        return "Primero guarda tu ubicación en Home"

    cercanos = usuarios_cercanos(m, 2)

    grupo_id = "_".join(sorted([m] + cercanos))

    if grupo_id not in grupos:
        grupos[grupo_id] = {"miembros": [m] + cercanos}

    return f"""
    <h2 style='text-align:center'>🚗 Grupo de Carpool</h2>

    <ul style='text-align:center'>
    {''.join([f"<li>{cuentas[u]['nombre']}</li>" for u in grupos[grupo_id]['miembros']])}
    </ul>

    <div style='text-align:center'>
    <a href="/chat_grupo/{grupo_id}">💬 Entrar al chat</a>
    </div>
    """

# 💬 CHATS (tipo IG)
@app.route("/chats/<m>")
def chats(m):

    html = "<h2 style='text-align:center'>💬 Chats</h2>"

    html += "<h3 style='text-align:center'>👤 Privados</h3>"

    for u in cuentas:
        if u != m:
            estado = "🟢" if u in online else "⚫"
            html += f"<p style='text-align:center'><a href='/chat/{m}/{u}'>{cuentas[u]['nombre']} {estado}</a></p>"

    html += "<h3 style='text-align:center'>👥 Grupos</h3>"

    for gid in grupos:
        if m in grupos[gid]["miembros"]:
            html += f"<p style='text-align:center'><a href='/chat_grupo/{gid}'>Grupo: {gid}</a></p>"

    html += f"<br><div style='text-align:center'><a href='/home/{m}'>⬅ Volver</a></div>"

    return html

# 💬 CHAT PRIVADO
@app.route("/chat/<yo>/<otro>", methods=["GET","POST"])
def chat(yo, otro):

    cid = tuple(sorted([yo,otro]))

    if cid not in mensajes:
        mensajes[cid] = []

    if request.method == "POST":
        mensajes[cid].append({
            "autor": yo,
            "texto": request.form["msg"]
        })

    html = f"<h3 style='text-align:center'>{cuentas[otro]['nombre']}</h3>"

    for msg in mensajes[cid]:
        if msg["autor"] == yo:
            html += f"<p style='text-align:right;color:blue;'>{msg['texto']}</p>"
        else:
            html += f"<p style='text-align:left;'>{msg['texto']}</p>"

    html += f"""
    <form method="post" style='text-align:center'>
    <input name="msg" placeholder="Mensaje">
    <button>Enviar</button>
    </form>

    <br>
    <div style='text-align:center'>
    <a href='/chats/{yo}'>⬅ Volver</a>
    </div>
    """

    return html

# 💬 CHAT GRUPO
@app.route("/chat_grupo/<gid>", methods=["GET","POST"])
def chat_grupo(gid):

    if gid not in mensajes:
        mensajes[gid] = []

    if request.method == "POST":
        mensajes[gid].append(request.form["msg"])

    html = "<h3 style='text-align:center'>👥 Chat de grupo</h3>"

    html += "<div style='text-align:center'><b>Miembros:</b><br>"
    for u in grupos[gid]["miembros"]:
        estado = "🟢" if u in online else "⚫"
        html += f"{cuentas[u]['nombre']} {estado}<br>"
    html += "</div><br>"

    for msg in mensajes[gid]:
        html += f"<p>{msg}</p>"

    html += """
    <form method="post" style='text-align:center'>
    <input name="msg" placeholder="Mensaje">
    <button>Enviar</button>
    </form>
    """

    return html

# 🚀 RUN
if __name__ == "__main__":
    app.run(port=5000)