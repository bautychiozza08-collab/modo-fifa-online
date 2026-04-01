from flask import Flask, render_template, request, redirect
import random

app = Flask(__name__)

equipo_usuario = None
dinero = 200
final = None
campeon = None

# =========================
# DATOS
# =========================
grupos = {
    "Grupo A": [
        {
            "nombre": "Real Madrid",
            "jugadores": [
                {"nombre": "Vinicius", "skill": 90, "forma": 80, "goles": 0, "precio": 120},
                {"nombre": "Bellingham", "skill": 88, "forma": 85, "goles": 0, "precio": 110},
            ]
        },
        {
            "nombre": "Bayern",
            "jugadores": [
                {"nombre": "Kane", "skill": 92, "forma": 85, "goles": 0, "precio": 130},
                {"nombre": "Musiala", "skill": 87, "forma": 82, "goles": 0, "precio": 100},
            ]
        },
        {
            "nombre": "Inter",
            "jugadores": [
                {"nombre": "Lautaro", "skill": 88, "forma": 83, "goles": 0, "precio": 105},
            ]
        },
        {
            "nombre": "Benfica",
            "jugadores": [
                {"nombre": "Di Maria", "skill": 87, "forma": 82, "goles": 0, "precio": 95},
            ]
        }
    ]
}

tabla = {"Grupo A": []}

def iniciar_tabla():
    tabla["Grupo A"] = []
    for e in grupos["Grupo A"]:
        tabla["Grupo A"].append({
            "equipo": e["nombre"],
            "pts":0,"pj":0,"gf":0,"gc":0
        })

iniciar_tabla()

# =========================
# FUNCIONES
# =========================
def obtener_equipo(nombre):
    return next(e for e in grupos["Grupo A"] if e["nombre"] == nombre)

def calcular_goles(eq):
    prom = sum(j["skill"]+j["forma"] for j in eq["jugadores"]) // len(eq["jugadores"])
    return prom//25 + random.randint(0,2)

def mejorar(eq, goles):
    for _ in range(goles):
        j = random.choice(eq["jugadores"])
        j["goles"] += 1
        j["forma"] = min(100, j["forma"]+3)

def actualizar(eq1, eq2, g1, g2):
    t = tabla["Grupo A"]
    e1 = next(e for e in t if e["equipo"]==eq1)
    e2 = next(e for e in t if e["equipo"]==eq2)

    e1["pj"]+=1; e2["pj"]+=1
    e1["gf"]+=g1; e1["gc"]+=g2
    e2["gf"]+=g2; e2["gc"]+=g1

    if g1>g2: e1["pts"]+=3
    elif g2>g1: e2["pts"]+=3
    else:
        e1["pts"]+=1
        e2["pts"]+=1

# =========================
# RUTA
# =========================
@app.route("/", methods=["GET","POST"])
def home():
    global equipo_usuario, dinero, final, campeon

    if request.method == "POST":

        if "elegir" in request.form:
            equipo_usuario = request.form["equipo"]

        if "jugar" in request.form and equipo_usuario:
            rival = random.choice([e for e in grupos["Grupo A"] if e["nombre"] != equipo_usuario])
            eq1 = obtener_equipo(equipo_usuario)
            eq2 = rival

            g1 = calcular_goles(eq1)
            g2 = calcular_goles(eq2)

            actualizar(eq1["nombre"], eq2["nombre"], g1, g2)
            mejorar(eq1, g1)
            mejorar(eq2, g2)

        if "simular" in request.form:
            eq1, eq2 = random.sample(grupos["Grupo A"], 2)

            g1 = calcular_goles(eq1)
            g2 = calcular_goles(eq2)

            actualizar(eq1["nombre"], eq2["nombre"], g1, g2)
            mejorar(eq1, g1)
            mejorar(eq2, g2)

        # 💰 FICHAJES
        if "fichar" in request.form and equipo_usuario:
            nombre = request.form["jugador"]

            for equipo in grupos["Grupo A"]:
                for j in equipo["jugadores"]:
                    if j["nombre"] == nombre and dinero >= j["precio"]:
                        dinero -= j["precio"]
                        user_team = obtener_equipo(equipo_usuario)
                        user_team["jugadores"].append(j)
                        equipo["jugadores"].remove(j)
                        break

        # 🏆 FINAL
        if "final" in request.form:
            mejores = sorted(tabla["Grupo A"], key=lambda x:x["pts"], reverse=True)[:2]
            final = (mejores[0]["equipo"], mejores[1]["equipo"])

        if "jugar_final" in request.form and final:
            eq1 = obtener_equipo(final[0])
            eq2 = obtener_equipo(final[1])

            g1 = calcular_goles(eq1)
            g2 = calcular_goles(eq2)

            campeon = final[0] if g1 > g2 else final[1]

        if "reset" in request.form:
            iniciar_tabla()
            dinero = 200
            equipo_usuario = None
            campeon = None
            for e in grupos["Grupo A"]:
                for j in e["jugadores"]:
                    j["goles"]=0
                    j["forma"]=80

        tabla["Grupo A"].sort(key=lambda x:(x["pts"], x["gf"]-x["gc"]), reverse=True)

        return redirect("/")

    tabla["Grupo A"].sort(key=lambda x:(x["pts"], x["gf"]-x["gc"]), reverse=True)

    return render_template("index.html",
        grupos=grupos,
        tabla=tabla,
        equipo_usuario=equipo_usuario,
        dinero=dinero,
        final=final,
        campeon=campeon
    )

if __name__ == "__main__":
    app.run(debug=True)