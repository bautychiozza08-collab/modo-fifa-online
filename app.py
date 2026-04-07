from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random
import string

app = Flask(__name__)
app.config["SECRET_KEY"] = "modo-fifa-secret"
socketio = SocketIO(app)

salas = {}


def crear_codigo():
    while True:
        codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if codigo not in salas:
            return codigo


def datos_iniciales():
    return {
        "equipos": [
            {
                "nombre": "Real Madrid",
                "jugadores": [
                    {"nombre": "Vinicius", "skill": 90, "forma": 80},
                    {"nombre": "Bellingham", "skill": 88, "forma": 85},
                ]
            },
            {
                "nombre": "Bayern",
                "jugadores": [
                    {"nombre": "Kane", "skill": 92, "forma": 85},
                    {"nombre": "Musiala", "skill": 87, "forma": 82},
                ]
            },
            {
                "nombre": "Inter",
                "jugadores": [
                    {"nombre": "Lautaro", "skill": 88, "forma": 83},
                    {"nombre": "Barella", "skill": 84, "forma": 80},
                ]
            },
            {
                "nombre": "Benfica",
                "jugadores": [
                    {"nombre": "Di Maria", "skill": 87, "forma": 82},
                    {"nombre": "Rafa Silva", "skill": 83, "forma": 79},
                ]
            }
        ]
    }


def calcular_goles(equipo):
    jugadores = equipo["jugadores"]
    promedio = sum(j["skill"] + j["forma"] for j in jugadores) // len(jugadores)
    return promedio // 25 + random.randint(0, 2)


def obtener_equipo(sala, nombre):
    for e in sala["equipos"]:
        if e["nombre"] == nombre:
            return e
    return None


def estado_publico(sala):
    return {
        "codigo": sala["codigo"],
        "jugadores": sala["jugadores"],
        "equipos": [e["nombre"] for e in sala["equipos"]],
        "listos": sala["listos"],
        "partido": sala["partido"],
        "historial": sala["historial"][-5:],
        "mensaje": sala["mensaje"],
    }


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("crear_sala")
def crear_sala(data):
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        emit("error_msg", {"mensaje": "Poné tu nombre."})
        return

    codigo = crear_codigo()
    base = datos_iniciales()

    salas[codigo] = {
        "codigo": codigo,
        "jugadores": [
            {
                "sid": request.sid,
                "nombre": nombre,
                "equipo": None
            }
        ],
        "equipos": base["equipos"],
        "listos": 0,
        "partido": None,
        "historial": [],
        "mensaje": f"{nombre} creó la sala.",
    }

    join_room(codigo)
    emit("sala_creada", {"codigo": codigo, "estado": estado_publico(salas[codigo])})


@socketio.on("unirse_sala")
def unirse_sala(data):
    nombre = (data.get("nombre") or "").strip()
    codigo = (data.get("codigo") or "").strip().upper()

    if not nombre or not codigo:
        emit("error_msg", {"mensaje": "Completá nombre y código."})
        return

    if codigo not in salas:
        emit("error_msg", {"mensaje": "La sala no existe."})
        return

    sala = salas[codigo]

    if len(sala["jugadores"]) >= 2:
        emit("error_msg", {"mensaje": "La sala ya está llena."})
        return

    sala["jugadores"].append({
        "sid": request.sid,
        "nombre": nombre,
        "equipo": None
    })

    sala["mensaje"] = f"{nombre} se unió a la sala."
    join_room(codigo)
    emit("estado_sala", estado_publico(sala), to=codigo)


@socketio.on("elegir_equipo")
def elegir_equipo(data):
    codigo = (data.get("codigo") or "").strip().upper()
    equipo = data.get("equipo")

    if codigo not in salas:
        emit("error_msg", {"mensaje": "Sala no encontrada."})
        return

    sala = salas[codigo]

    jugador_actual = None
    for j in sala["jugadores"]:
        if j["sid"] == request.sid:
            jugador_actual = j
            break

    if not jugador_actual:
        emit("error_msg", {"mensaje": "No estás dentro de esta sala."})
        return

    for j in sala["jugadores"]:
        if j["sid"] != request.sid and j["equipo"] == equipo:
            emit("error_msg", {"mensaje": "Ese equipo ya fue elegido."})
            return

    jugador_actual["equipo"] = equipo
    sala["mensaje"] = f"{jugador_actual['nombre']} eligió {equipo}."
    emit("estado_sala", estado_publico(sala), to=codigo)


@socketio.on("jugador_listo")
def jugador_listo(data):
    codigo = (data.get("codigo") or "").strip().upper()

    if codigo not in salas:
        emit("error_msg", {"mensaje": "Sala no encontrada."})
        return

    sala = salas[codigo]

    jugador_actual = None
    for j in sala["jugadores"]:
        if j["sid"] == request.sid:
            jugador_actual = j
            break

    if not jugador_actual:
        emit("error_msg", {"mensaje": "No estás dentro de esta sala."})
        return

    if not jugador_actual["equipo"]:
        emit("error_msg", {"mensaje": "Primero elegí un equipo."})
        return

    sala["listos"] += 1
    if sala["listos"] > len(sala["jugadores"]):
        sala["listos"] = len(sala["jugadores"])

    if len(sala["jugadores"]) == 2 and sala["listos"] == 2:
        j1 = sala["jugadores"][0]
        j2 = sala["jugadores"][1]

        eq1 = obtener_equipo(sala, j1["equipo"])
        eq2 = obtener_equipo(sala, j2["equipo"])

        g1 = calcular_goles(eq1)
        g2 = calcular_goles(eq2)

        if g1 > g2:
            ganador = j1["nombre"]
        elif g2 > g1:
            ganador = j2["nombre"]
        else:
            ganador = "Empate"

        sala["partido"] = {
            "local_nombre": j1["nombre"],
            "local_equipo": j1["equipo"],
            "visitante_nombre": j2["nombre"],
            "visitante_equipo": j2["equipo"],
            "g1": g1,
            "g2": g2,
            "ganador": ganador
        }

        sala["historial"].append(sala["partido"])
        sala["mensaje"] = "Partido jugado."
        sala["listos"] = 0

    else:
        sala["mensaje"] = f"{jugador_actual['nombre']} está listo."

    emit("estado_sala", estado_publico(sala), to=codigo)


@socketio.on("reiniciar_partido")
def reiniciar_partido(data):
    codigo = (data.get("codigo") or "").strip().upper()

    if codigo not in salas:
        emit("error_msg", {"mensaje": "Sala no encontrada."})
        return

    sala = salas[codigo]
    sala["partido"] = None
    sala["listos"] = 0
    sala["mensaje"] = "Nueva ronda lista."
    emit("estado_sala", estado_publico(sala), to=codigo)


@socketio.on("disconnect")
def salir():
    sala_a_borrar = None

    for codigo, sala in salas.items():
        antes = len(sala["jugadores"])
        sala["jugadores"] = [j for j in sala["jugadores"] if j["sid"] != request.sid]

        if len(sala["jugadores"]) != antes:
            sala["listos"] = 0
            sala["partido"] = None
            sala["mensaje"] = "Un jugador salió de la sala."
            emit("estado_sala", estado_publico(sala), to=codigo)

        if len(sala["jugadores"]) == 0:
            sala_a_borrar = codigo

    if sala_a_borrar:
        del salas[sala_a_borrar]


if __name__ == "__main__":
    socketio.run(app, debug=True)