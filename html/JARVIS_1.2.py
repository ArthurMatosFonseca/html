import sqlite3
from datetime import datetime
import threading
import time
import re
import math
import ast
import operator

# ============================================================
# J.A.R.V.I.S 1.2
# Núcleo + Interface + Memória SQLite
# Modo Matemática + Interpretador Matemático Seguro (AST Parser)
# ============================================================

VERSION = "1.2"
DATABASE = "jarvis.db"

# Atualização automática da hora a cada 5 minutos
INTERVALO_HORA = 5 * 60

# Controle dos modos
MODO_MATEMATICA = False

# Lock para sincronização de I/O de console entre threads
PRINT_LOCK = threading.Lock()


# ============================================================
# BANCO DE DADOS
# ============================================================

def conectar_banco():
    return sqlite3.connect(DATABASE, timeout=10.0)


def inicializar_banco():
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conteudo TEXT NOT NULL,
                criado_em TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS variaveis (
                simbolo TEXT PRIMARY KEY,
                valor REAL NOT NULL,
                tipo TEXT,
                atualizado_em TEXT NOT NULL
            )
        """)
        conexao.commit()
    finally:
        conexao.close()


# ============================================================
# MEMÓRIA NORMAL
# ============================================================

def salvar_memoria(conteudo):
    conexao = conectar_banco()
    try:
        data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        conexao.execute("""
            INSERT INTO memoria (conteudo, criado_em)
            VALUES (?, ?)
        """, (conteudo, data))
        conexao.commit()
    finally:
        conexao.close()


def listar_memorias():
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id, conteudo, criado_em
            FROM memoria
            ORDER BY id
        """)
        return cursor.fetchall()
    finally:
        conexao.close()


def apagar_memorias():
    conexao = conectar_banco()
    try:
        conexao.execute("DELETE FROM memoria")
        conexao.commit()
    finally:
        conexao.close()


# ============================================================
# MEMÓRIA MATEMÁTICA
# ============================================================

def salvar_variavel(simbolo, valor, tipo="numero"):
    conexao = conectar_banco()
    try:
        data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        conexao.execute("""
            INSERT OR REPLACE INTO variaveis
            (simbolo, valor, tipo, atualizado_em)
            VALUES (?, ?, ?, ?)
        """, (simbolo, valor, tipo, data))
        conexao.commit()
    finally:
        conexao.close()


def obter_variavel(simbolo):
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT valor, tipo
            FROM variaveis
            WHERE simbolo = ?
        """, (simbolo,))
        return cursor.fetchone()
    finally:
        conexao.close()


def listar_variaveis():
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT simbolo, valor, tipo
            FROM variaveis
            ORDER BY simbolo
        """)
        return cursor.fetchall()
    finally:
        conexao.close()


def apagar_variaveis():
    conexao = conectar_banco()
    try:
        conexao.execute("DELETE FROM variaveis")
        conexao.commit()
    finally:
        conexao.close()


# ============================================================
# DATA E HORA
# ============================================================

def obter_hora():
    return datetime.now().strftime("%H:%M:%S")


def obter_data():
    return datetime.now().strftime("%d/%m/%Y")


# ============================================================
# ATUALIZAÇÃO AUTOMÁTICA DA HORA
# ============================================================

def atualizar_hora_automaticamente():
    while True:
        time.sleep(INTERVALO_HORA)
        # Sincroniza a impressão para evitar sobreposição no terminal
        with PRINT_LOCK:
            print(f"\n[JARVIS Notificação] Atualização automática da hora: {obter_hora()}\nVocê > ", end="", flush=True)


def iniciar_atualizacao_hora():
    thread_hora = threading.Thread(
        target=atualizar_hora_automaticamente,
        daemon=True
    )
    thread_hora.start()


# ============================================================
# FERRAMENTAS MATEMÁTICAS & AVALIADOR SEGURO (AST)
# ============================================================

def converter_numero(valor):
    valor = str(valor).strip()
    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif "," in valor:
        valor = valor.replace(",", ".")
    return float(valor)


def formatar_numero(valor):
    if abs(valor) < 1e-12:
        valor = 0
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.6f}".rstrip("0").rstrip(".").replace(".", ",")


def formatar_porcentagem(valor):
    return f"{formatar_numero(valor)}%"


# Avaliador matemático AST 100% seguro contra RCE / Negação de Serviço
OPERACOES_PERMITIDAS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def avaliar_ast_no(node, variaveis_env=None):
    if variaveis_env is None:
        variaveis_env = {}

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Constante inválida")

    elif isinstance(node, ast.Name):
        if node.id in variaveis_env:
            return float(variaveis_env[node.id])
        raise ValueError(f"Variável não definida: {node.id}")

    elif isinstance(node, ast.BinOp):
        tipo_op = type(node.op)
        if tipo_op in OPERACOES_PERMITIDAS:
            esq = avaliar_ast_no(node.left, variaveis_env)
            dir_val = avaliar_ast_no(node.right, variaveis_env)
            
            # Proteção contra expoentes excessivos (DoS)
            if tipo_op == ast.Pow and (dir_val > 1000 or esq > 1e10):
                raise ValueError("Exponenciação muito grande")
                
            return OPERACOES_PERMITIDAS[tipo_op](esq, dir_val)
        raise ValueError(f"Operação não permitida: {tipo_op}")

    elif isinstance(node, ast.UnaryOp):
        tipo_op = type(node.op)
        if tipo_op in OPERACOES_PERMITIDAS:
            val = avaliar_ast_no(node.operand, variaveis_env)
            return OPERACOES_PERMITIDAS[tipo_op](val)
        raise ValueError(f"Operação unária não permitida: {tipo_op}")

    else:
        raise ValueError("Sintaxe matemática não suportada")


def avaliar_expressao_segura(expressao_str, variaveis_env=None):
    try:
        arvore = ast.parse(expressao_str, mode='eval')
        return avaliar_ast_no(arvore.body, variaveis_env)
    except Exception:
        return None


# ============================================================
# VARIÁVEIS MATEMÁTICAS
# ============================================================

def interpretar_variavel(texto):
    texto_limpo = texto.strip().lower()

    padrao = re.search(
        r"^\s*([a-zA-Z][a-zA-Z0-9]*)\s*=\s*"
        r"([-+]?\d+(?:[.,]\d+)?)\s*%?\s*$",
        texto_limpo
    )

    if padrao:
        simbolo = padrao.group(1)
        valor = converter_numero(padrao.group(2))
        eh_porcentagem = "%" in texto_limpo

        if eh_porcentagem:
            salvar_variavel("%", valor, "porcentagem")
            return f"% armazenado: {formatar_porcentagem(valor)}"

        salvar_variavel(simbolo, valor, "numero")
        return f"{simbolo} armazenado: {formatar_numero(valor)}"

    padrao_porcentagem = re.search(
        r"^\s*%\s*=\s*([-+]?\d+(?:[.,]\d+)?)\s*%?\s*$",
        texto_limpo
    )

    if padrao_porcentagem:
        valor = converter_numero(padrao_porcentagem.group(1))
        salvar_variavel("%", valor, "porcentagem")
        return f"% armazenado: {formatar_porcentagem(valor)}"

    return None


def interpretar_valor_nomeado(texto):
    texto_limpo = texto.lower()

    # Mapeamento de buscas parametrizadas para evitar linhas duplicadas
    regras = [
        (r"(?:capital|principal|valor inicial).*?([-+]?\d+(?:[.,]\d+)?)", "C", "capital", "Capital C armazenado"),
        (r"(?:taxa|porcentagem|juros).*?([-+]?\d+(?:[.,]\d+)?)\s*%", "%", "porcentagem", "Taxa % armazenada"),
        (r"(?:tempo|prazo).*?([-+]?\d+(?:[.,]\d+)?)", "t", "tempo", "Tempo t armazenado")
    ]

    for padrao, simbolo, tipo, msg in regras:
        match = re.search(padrao, texto_limpo)
        if match:
            valor = converter_numero(match.group(1))
            salvar_variavel(simbolo, valor, tipo)
            fmt = formatar_porcentagem(valor) if tipo == "porcentagem" else formatar_numero(valor)
            return f"{msg}: {fmt}"

    return None


# ============================================================
# CALCULADORA DIRETA
# ============================================================

def calcular_expressao(texto):
    expressao = texto.strip()

    if not re.search(r"\d", expressao) or "=" in expressao:
        return None

    if re.search(r"[a-wyzA-WYZ]", expressao):
        return None

    if not re.fullmatch(r"[0-9+\-*/().,%^ xX]+", expressao):
        return None

    expressao = expressao.replace("^", "**").replace("X", "*").replace("x", "*").replace(",", ".")

    # 10% → (10/100)
    expressao = re.sub(r"(\d+(?:\.\d+)?)%", r"(/100)", expressao)

    resultado = avaliar_expressao_segura(expressao)

    if resultado is not None:
        return (
            "RESULTADO MATEMÁTICO\n"
            "-------------------------\n"
            f"{formatar_numero(resultado)}"
        )

    return None


# ============================================================
# JUROS (SIMPLES E COMPOSTOS)
# ============================================================

def obter_taxa_decimal():
    resultado = obter_variavel("%")
    if not resultado:
        return None
    valor, tipo = resultado
    return valor / 100 if tipo == "porcentagem" else valor


def calcular_juros_generico(modo="simples"):
    capital = obter_variavel("C")
    taxa = obter_taxa_decimal()
    tempo = obter_variavel("t")

    faltantes = []
    if not capital:
        faltantes.append("C = capital")
    if taxa is None:
        faltantes.append("% = taxa")
    if not tempo:
        faltantes.append("t = tempo")

    formula = "J = C × i × t" if modo == "simples" else "M = C × (1 + i)^t"

    if faltantes:
        resposta = (
            "DADOS INSUFICIENTES\n"
            "-------------------------\n"
            f"Fórmula: {formula}\n\n"
        )
        if capital:
            resposta += f"C = {formatar_numero(capital[0])}\n"
        if taxa is not None:
            resposta += f"i = {formatar_numero(taxa)}\n"
        if tempo:
            resposta += f"t = {formatar_numero(tempo[0])}\n"

        resposta += "\nDADO(S) FALTANTE(S):\n" + "\n".join(f"- {f}" for f in faltantes) + "\n\nInforme o valor faltante."
        return resposta

    c_val = capital[0]
    t_val = tempo[0]

    if modo == "simples":
        juros = c_val * taxa * t_val
        montante = c_val + juros
        nome_calculo = "JUROS SIMPLES"
    else:
        montante = c_val * ((1 + taxa) ** t_val)
        juros = montante - c_val
        nome_calculo = "JUROS COMPOSTOS"

    return (
        f"CÁLCULO DE {nome_calculo}\n"
        "-------------------------\n"
        f"Fórmula: {formula}\n\n"
        f"C = {formatar_numero(c_val)}\n"
        f"i = {formatar_numero(taxa)}\n"
        f"t = {formatar_numero(t_val)}\n\n"
        f"Juros = {formatar_numero(juros)}\n"
        f"Montante = {formatar_numero(montante)}"
    )


def interpretar_juros_simples(texto):
    return calcular_juros_generico(modo="simples")


def interpretar_juros_compostos(texto):
    return calcular_juros_generico(modo="compostos")


# ============================================================
# EQUAÇÃO DE 1º GRAU
# ============================================================

def interpretar_equacao_primeiro_grau(texto):
    expressao = texto.lower().replace(" ", "").replace(",", ".")

    padrao = re.search(
        r"([+-]?\d+(?:\.\d+)?)x"
        r"([+-]\d+(?:\.\d+)?)?"
        r"="
        r"([+-]?\d+(?:\.\d+)?)",
        expressao
    )

    if not padrao:
        return None

    a = float(padrao.group(1))
    b = float(padrao.group(2)) if padrao.group(2) else 0.0
    c = float(padrao.group(3))

    if a == 0:
        return "Não é possível dividir por zero em equação de 1º grau."

    x = (c - b) / a

    salvar_variavel("a", a, "coeficiente")
    salvar_variavel("b", b, "coeficiente")
    salvar_variavel("c", c, "resultado")

    return (
        "EQUAÇÃO DE 1º GRAU\n"
        "-------------------------\n"
        f"{formatar_numero(a)}x + {formatar_numero(b)} = {formatar_numero(c)}\n\n"
        "x = (c - b) / a\n\n"
        f"x = {formatar_numero(x)}"
    )


# ============================================================
# EQUAÇÃO DE 2º GRAU / BHASKARA
# ============================================================

def normalizar_equacao_quadratica(texto):
    texto = texto.lower().strip()

    # Normalização de caracteres
    substituicoes = [
        ("²", "^2"), ("³", "^3"), ("−", "-"), ("–", "-"), ("—", "-"),
        ("×", "*"), ("÷", "/"), (",", ".")
    ]
    for orig, sub in substituicoes:
        texto = texto.replace(orig, sub)

    comandos = [
        r"resolva", r"resolver", r"calcule", r"calcular",
        r"calcula", r"encontre", r"encontrar", r"determine",
        r"determinar", r"ach[eé]", r"achar", r"obtenha",
        r"obter", r"descubra", r"descobrir", r"raízes?\s+de",
        r"raizes?\s+de", r"equação", r"equacao", r"equações",
        r"equacoes", r"segundo\s+grau", r"2º\s+grau", r"2o\s+grau",
        r"2\s+grau", r"quadrática", r"quadratica", r"bhaskara",
        r"baskara"
    ]

    texto_sem_comando = texto
    for comando in comandos:
        texto_sem_comando = re.sub(comando, " ", texto_sem_comando)

    candidatos = re.findall(r"[0-9xX\^\+\-\*\/\.\(\)\=\s]+", texto_sem_comando)

    if not candidatos:
        return None

    expressao = max(candidatos, key=len).strip()
    expressao = re.sub(r"\s+", "", expressao)

    if "x" not in expressao:
        return None

    if "=" in expressao:
        partes = expressao.split("=")
        if len(partes) != 2:
            return None
        esquerda, direita = partes[0].strip(), partes[1].strip()
        if not esquerda:
            return None
        if not direita:
            direita = "0"
        polinomio = esquerda if direita == "0" else f"{esquerda}-({direita})"
    else:
        polinomio = expressao

    polinomio = polinomio.replace("X", "x")

    if not re.fullmatch(r"[0-9x\^\+\-\*\/\.\(\)]+", polinomio):
        return None

    if "x^2" not in polinomio:
        return None

    return polinomio


def extrair_coeficientes_quadratica(expressao):
    expr = expressao.lower().replace(" ", "").replace("^", "**")

    # Inserção segura de multiplicação implícita
    expr = re.sub(r"(\d|\))(?=x|\()", r"*", expr)
    expr = re.sub(r"x(?=\()", "x*", expr)
    expr = re.sub(r"(\))(?=\d)", r"*", expr)

    if not re.fullmatch(r"[0-9x\+\-\*\/\.\(\)]+", expr) or "x**2" not in expr:
        return None

    def avaliar(x_val):
        return avaliar_expressao_segura(expr, {"x": x_val})

    p0 = avaliar(0)
    p1 = avaliar(1)
    pm1 = avaliar(-1)

    if p0 is None or p1 is None or pm1 is None:
        return None

    a = (p1 + pm1 - 2 * p0) / 2
    b = (p1 - pm1) / 2
    c = p0

    if abs(a) < 1e-12:
        return None

    return a, b, c


def resolver_bhaskara(a, b, c):
    if abs(a) < 1e-12:
        return (
            "ERRO MATEMÁTICO\n"
            "-------------------------\n"
            "O coeficiente 'a' não pode ser zero em uma equação de 2º grau."
        )

    delta = b ** 2 - 4 * a * c
    if abs(delta) < 1e-12:
        delta = 0.0

    resposta = (
        "EQUAÇÃO DE 2º GRAU\n"
        "-------------------------\n"
        f"a = {formatar_numero(a)}\n"
        f"b = {formatar_numero(b)}\n"
        f"c = {formatar_numero(c)}\n\n"
        "Fórmula:\n"
        "Δ = b² - 4ac\n\n"
        f"Δ = ({formatar_numero(b)})² - 4 × ({formatar_numero(a)}) × ({formatar_numero(c)})\n"
        f"Δ = {formatar_numero(delta)}\n\n"
    )

    if delta < 0:
        resposta += (
            "Classificação:\n"
            "Δ < 0 → não existem raízes reais.\n\n"
            "Existem duas raízes complexas conjugadas."
        )
        return resposta

    if delta == 0:
        x = -b / (2 * a)
        salvar_variavel("a", a, "coeficiente")
        salvar_variavel("b", b, "coeficiente")
        salvar_variavel("c", c, "coeficiente")
        salvar_variavel("x1", x, "raiz dupla")
        salvar_variavel("x2", x, "raiz dupla")
        salvar_variavel("delta", delta, "discriminante")

        resposta += (
            "Classificação:\n"
            "Δ = 0 → existe uma raiz real dupla.\n\n"
            "Fórmula:\n"
            "x = -b / (2a)\n\n"
            f"x = {formatar_numero(x)}\n\n"
            "Verificação:\n"
            f"P({formatar_numero(x)}) = 0"
        )
        return resposta

    raiz_delta = math.sqrt(delta)
    x1 = (-b + raiz_delta) / (2 * a)
    x2 = (-b - raiz_delta) / (2 * a)

    verificacao1 = a * x1 ** 2 + b * x1 + c
    verificacao2 = a * x2 ** 2 + b * x2 + c

    if abs(verificacao1) < 1e-10:
        verificacao1 = 0
    if abs(verificacao2) < 1e-10:
        verificacao2 = 0

    salvar_variavel("a", a, "coeficiente")
    salvar_variavel("b", b, "coeficiente")
    salvar_variavel("c", c, "coeficiente")
    salvar_variavel("delta", delta, "discriminante")
    salvar_variavel("x1", x1, "raiz")
    salvar_variavel("x2", x2, "raiz")

    resposta += (
        "Classificação:\n"
        "Δ > 0 → existem duas raízes reais distintas.\n\n"
        "Fórmula:\n"
        "x₁,₂ = (-b ± √Δ) / (2a)\n\n"
        f"√Δ = {formatar_numero(raiz_delta)}\n\n"
        f"x₁ = {formatar_numero(x1)}\n"
        f"x₂ = {formatar_numero(x2)}\n\n"
        "Verificação:\n"
        f"P(x₁) = {formatar_numero(verificacao1)}\n"
        f"P(x₂) = {formatar_numero(verificacao2)}"
    )

    return resposta


def interpretar_bhaskara(texto):
    expressao = normalizar_equacao_quadratica(texto)
    if not expressao:
        return None

    coeficientes = extrair_coeficientes_quadratica(expressao)
    if not coeficientes:
        return None

    a, b, c = coeficientes
    return resolver_bhaskara(a, b, c)


# ============================================================
# PROGRESSÃO ARITMÉTICA E GEOMÉTRICA (DRY Refactored)
# ============================================================

def extrair_parametro(padrao, texto, nome_var):
    match = re.search(padrao, texto)
    if match:
        val = match.group(1)
        return int(val) if nome_var == "n" else converter_numero(val)
    
    salvo = obter_variavel(nome_var)
    if salvo:
        return int(salvo[0]) if nome_var == "n" else salvo[0]
    return None


def interpretar_pa(texto):
    texto_l = texto.lower()
    a1 = extrair_parametro(r"a1\s*=?\s*(-?\d+(?:[.,]\d+)?)", texto_l, "a1")
    r = extrair_parametro(r"r\s*=?\s*(-?\d+(?:[.,]\d+)?)", texto_l, "r")
    n = extrair_parametro(r"n\s*=?\s*(\d+)", texto_l, "n")

    faltantes = []
    if a1 is None: faltantes.append("a1 = primeiro termo")
    if r is None: faltantes.append("r = razão")
    if n is None: faltantes.append("n = número de termos")

    if faltantes:
        return (
            "DADOS INSUFICIENTES\n"
            "-------------------------\n"
            "Fórmula: an = a1 + (n - 1)r\n\n"
            "DADO(S) FALTANTE(S):\n"
            + "\n".join(f"- {f}" for f in faltantes)
            + "\n\nInforme o valor faltante."
        )

    an = a1 + (n - 1) * r
    soma = n * (a1 + an) / 2

    salvar_variavel("a1", a1, "primeiro termo")
    salvar_variavel("r", r, "razao")
    salvar_variavel("n", n, "numero de termos")

    return (
        "PROGRESSÃO ARITMÉTICA\n"
        "-------------------------\n"
        "an = a1 + (n - 1)r\n"
        "Sn = n(a1 + an) / 2\n\n"
        f"a1 = {formatar_numero(a1)}\n"
        f"r = {formatar_numero(r)}\n"
        f"n = {n}\n\n"
        f"an = {formatar_numero(an)}\n"
        f"Sn = {formatar_numero(soma)}"
    )


def interpretar_pg(texto):
    texto_l = texto.lower()
    a1 = extrair_parametro(r"a1\s*=?\s*(-?\d+(?:[.,]\d+)?)", texto_l, "a1")
    q = extrair_parametro(r"q\s*=?\s*(-?\d+(?:[.,]\d+)?)", texto_l, "q")
    n = extrair_parametro(r"n\s*=?\s*(\d+)", texto_l, "n")

    faltantes = []
    if a1 is None: faltantes.append("a1 = primeiro termo")
    if q is None: faltantes.append("q = razão")
    if n is None: faltantes.append("n = número de termos")

    if faltantes:
        return (
            "DADOS INSUFICIENTES\n"
            "-------------------------\n"
            "Fórmula: an = a1 × q^(n - 1)\n\n"
            "DADO(S) FALTANTE(S):\n"
            + "\n".join(f"- {f}" for f in faltantes)
            + "\n\nInforme o valor faltante."
        )

    an = a1 * (q ** (n - 1))
    soma = a1 * n if q == 1 else a1 * (q ** n - 1) / (q - 1)

    salvar_variavel("a1", a1, "primeiro termo")
    salvar_variavel("q", q, "razao")
    salvar_variavel("n", n, "numero de termos")

    return (
        "PROGRESSÃO GEOMÉTRICA\n"
        "-------------------------\n"
        "an = a1 × q^(n - 1)\n\n"
        f"a1 = {formatar_numero(a1)}\n"
        f"q = {formatar_numero(q)}\n"
        f"n = {n}\n\n"
        f"an = {formatar_numero(an)}\n"
        f"Sn = {formatar_numero(soma)}"
    )


# ============================================================
# INTERPRETADOR MATEMÁTICO
# ============================================================

def interpretar_matematica(texto):
    texto_lower = texto.lower()

    # Variáveis e Nomeações
    res = interpretar_variavel(texto) or interpretar_valor_nomeado(texto)
    if res:
        return res

    # Juros
    if any(k in texto_lower for k in ["juros simples", "calculo de juros simples", "cálculo de juros simples"]):
        return interpretar_juros_simples(texto)

    if any(k in texto_lower for k in ["juros compostos", "calculo de juros compostos", "cálculo de juros compostos"]):
        return interpretar_juros_compostos(texto)

    # Equação de 2º Grau / Bhaskara
    gatilhos_quadratica = ["bhaskara", "baskara", "2 grau", "2º grau", "segundo grau", "quadratica", "quadrática", "x²", "x^2"]
    if any(k in texto_lower for k in gatilhos_quadratica) or ("x2" in texto_lower and "=" in texto_lower):
        res = interpretar_bhaskara(texto)
        if res:
            return res

    # Equação de 1º Grau
    if any(k in texto_lower for k in ["1 grau", "1º grau", "primeiro grau"]) or "=" in texto:
        res = interpretar_equacao_primeiro_grau(texto)
        if res:
            return res

    # PA / PG
    if re.search(r"pa", texto_lower) or "progressão aritmética" in texto_lower or "progressao aritmetica" in texto_lower:
        return interpretar_pa(texto)

    if re.search(r"pg", texto_lower) or "progressão geométrica" in texto_lower or "progressao geometrica" in texto_lower:
        return interpretar_pg(texto)

    # Expressão Direta
    return calcular_expressao(texto)


# ============================================================
# MODO MATEMÁTICA
# ============================================================

def iniciar_modo_matematica():
    return (
        "\n"
        "============================================\n"
        "          JARVIS 1.2: MATEMÁTICA\n"
        "============================================\n"
        "MODO MATEMÁTICO ATIVADO.\n\n"
        "Agora interpreto contas, equações e problemas matemáticos.\n\n"
        "Exemplos:\n"
        "  25 + 37\n"
        "  144 / 12\n"
        "  2^10\n"
        "  2x + 4 = 36\n"
        "  x² - 5x + 6 = 0\n"
        "  C = 5000\n"
        "  % = 3\n"
        "  t = 8\n"
        "  juros simples\n"
        "  juros compostos\n"
        "  PA\n"
        "  PG\n\n"
        'Digite "sair matemática" para retornar.\n'
        "============================================\n"
    )


# ============================================================
# ROUTER DE RESPOSTAS (Refatorado & Limpo)
# ============================================================

def responder(mensagem):
    global MODO_MATEMATICA
    texto = mensagem.strip().lower()

    if texto in ["matemática", "matematica"]:
        MODO_MATEMATICA = True
        return iniciar_modo_matematica()

    if texto in ["sair matemática", "sair matematica", "fechar matemática", "fechar matematica"]:
        MODO_MATEMATICA = False
        return "Modo matemática encerrado.\nJARVIS > Retornando ao modo normal."

    if MODO_MATEMATICA:
        resultado = interpretar_matematica(mensagem)
        return resultado if resultado else (
            "Não consegui interpretar essa expressão matemática.\n"
            "Digite uma conta, equação ou problema matemático."
        )

    # Sistema Normal - Comandos
    if texto in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return f"Olá. JARVIS {VERSION} online e pronto."

    if any(k in texto for k in ["tudo bem", "como voce esta", "como você está", "como vai"]):
        return "Todos os sistemas principais estão funcionando normalmente."

    if texto in ["hora", "horas", "horario", "horário", "que horas"]:
        return f"Agora são {obter_hora()}."

    if texto in ["data", "que dia", "data atual"]:
        return f"Hoje é {obter_data()}."

    if any(k in texto for k in ["quem e voce", "quem é você", "qual seu nome"]):
        return f"Sou JARVIS, versão {VERSION}. Estou em desenvolvimento."

    if texto == "status":
        q_mem = len(listar_memorias())
        q_var = len(listar_variaveis())
        modo = "MATEMÁTICA" if MODO_MATEMATICA else "NORMAL"
        return (
            "STATUS DO JARVIS\n"
            "-------------------------\n"
            "Núcleo: ONLINE\n"
            "Interface: ONLINE\n"
            "Banco de dados: ONLINE (Modo WAL)\n"
            "Memória: ATIVA\n"
            "Memória matemática: ATIVA\n"
            "Interpretador matemático: ONLINE (Seguro AST)\n"
            "Relógio automático: ONLINE\n"
            f"Modo atual: {modo}\n"
            f"Memórias: {q_mem}\n"
            f"Variáveis: {q_var}\n"
            f"Versão: {VERSION}"
        )

    # Armazenamento de Memória
    prefixos_memoria = ["lembrar que ", "lembre que "]
    for pref in prefixos_memoria:
        if texto.startswith(pref):
            conteudo = mensagem[len(pref):].strip()
            if conteudo:
                salvar_memoria(conteudo)
                return "Informação armazenada na minha memória."

    if texto in ["o que você lembra", "o que voce lembra", "memoria", "memória", "listar memorias", "listar memórias"]:
        memorias = listar_memorias()
        if not memorias:
            return "Minha memória está vazia."
        resposta = "MEMÓRIA DO JARVIS\n-------------------------\n"
        for id_m, cont, dt in memorias:
            resposta += f"{id_m}. {cont}\n   Registrado: {dt}\n"
        return resposta

    if texto in ["variaveis", "variáveis", "memoria matematica", "memória matemática", "dados matematicos", "dados matemáticos"]:
        variaveis = listar_variaveis()
        if not variaveis:
            return "A memória matemática está vazia."
        resposta = "MEMÓRIA MATEMÁTICA DO JARVIS\n-------------------------\n"
        for sim, val, tp in variaveis:
            val_txt = formatar_porcentagem(val) if tp == "porcentagem" else formatar_numero(val)
            resposta += f"{sim} = {val_txt} ({tp})\n"
        return resposta

    if texto in ["apagar memoria", "apagar memória", "limpar memoria", "limpar memória"]:
        apagar_memorias()
        return "Memória apagada."

    if texto in ["apagar variaveis", "apagar variáveis", "limpar variaveis", "limpar variáveis", "limpar memoria matematica", "limpar memória matemática"]:
        apagar_variaveis()
        return "Memória matemática apagada."

    if texto in ["ajuda", "help", "comandos"]:
        return (
            "COMANDOS DISPONÍVEIS\n"
            "-------------------------\n"
            "oi | tudo bem | horas | data | quem é você | status\n\n"
            "MEMÓRIA\n"
            "-------------------------\n"
            "lembrar que ...\n"
            "o que você lembra\n"
            "variáveis\n"
            "apagar memória | apagar variáveis\n\n"
            "MATEMÁTICA\n"
            "-------------------------\n"
            "matemática\n"
            "25 + 37 | 2x + 4 = 36 | x² - 5x + 6 = 0\n"
            "C = 5000 | % = 3 | t = 8\n"
            "juros simples | juros compostos | PA | PG\n"
            "sair matemática\n\n"
            "sair"
        )

    if texto in ["sair", "encerrar", "desligar"]:
        return "__SAIR__"

    return "Ainda não compreendi essa solicitação."


# ============================================================
# INICIALIZAÇÃO E LOOP PRINCIPAL
# ============================================================

def iniciar():
    inicializar_banco()
    print("=" * 60)
    print(" J.A.R.V.I.S")
    print(" SYSTEM ONLINE")
    print("=" * 60)
    print(f"Versão: {VERSION}")
    print("Núcleo: ONLINE")
    print("Interface: ONLINE")
    print("Banco de dados: ONLINE (Modo WAL)")
    print("Memória: ATIVA")
    print("Memória matemática: ATIVA")
    print("Interpretador matemático: ONLINE (Seguro AST)")
    print("Relógio automático: ONLINE")
    print("Digite 'ajuda' para comandos.\n")


def main():
    iniciar()
    iniciar_atualizacao_hora()

    while True:
        try:
            with PRINT_LOCK:
                mensagem = input("Você > ")
        except (KeyboardInterrupt, EOFError):
            print("\nJARVIS > Encerrando sistema...")
            break
        except Exception as erro:
            print(f"\nJARVIS > Erro: {erro}")
            continue

        if not mensagem.strip():
            continue

        try:
            resposta = responder(mensagem)
        except Exception as erro:
            print(f"\nJARVIS > Erro ao processar comando: {erro}")
            continue

        if resposta == "__SAIR__":
            print("JARVIS > Encerrando sistema...")
            break

        print(f"\nJARVIS > {resposta}\n")


# ============================================================
# EXECUÇÃO (Sem erros de sintaxe)
# ============================================================

if __name__ == "__main__":
    main()
