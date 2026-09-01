```python
import mysql.connector
import threading
import time
from datetime import datetime, timedelta


class MemoriaJarvis:

    def __init__(self):

        # =====================================================
        # CONFIGURAÇÃO DO BANCO DE DADOS
        # =====================================================

        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'SuaSenha',  # Substitua pela sua senha
            'database': 'jarvis_cerebro'
        }

        # =====================================================
        # HORÁRIO INTERNO DO JARVIS
        # =====================================================

        self.hora_atual = datetime.now()

        # =====================================================
        # INICIALIZAÇÃO DAS TABELAS
        # =====================================================

        self._inicializar_tabela_lembretes()

        # =====================================================
        # CONTROLE DAS THREADS
        # =====================================================

        self.executando = True

        # Thread responsável pela atualização do horário
        self.thread_tempo = threading.Thread(
            target=self._loop_atualizacao_tempo,
            daemon=True
        )

        self.thread_tempo.start()

        # Thread responsável por verificar os lembretes
        self.thread_lembretes = threading.Thread(
            target=self._loop_verificacao_lembretes,
            daemon=True
        )

        self.thread_lembretes.start()

    # =========================================================
    # CONEXÃO COM O MYSQL
    # =========================================================

    def _conectar(self):

        return mysql.connector.connect(**self.config)

    # =========================================================
    # TABELA DE LEMBRETES
    # =========================================================

    def _inicializar_tabela_lembretes(self):

        """Cria a tabela de lembretes caso ainda não exista."""

        query = """
        CREATE TABLE IF NOT EXISTS lembretes (

            id INT AUTO_INCREMENT PRIMARY KEY,

            descricao VARCHAR(255) NOT NULL,

            horario DATETIME NOT NULL,

            status ENUM(
                'pendente',
                'concluido'
            ) DEFAULT 'pendente',

            criado_em TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        );
        """

        conn = self._conectar()

        cursor = conn.cursor()

        cursor.execute(query)

        conn.commit()

        cursor.close()

        conn.close()

    # =========================================================
    # ATUALIZAÇÃO DO HORÁRIO
    # =========================================================

    def _loop_atualizacao_tempo(self):

        """
        Atualiza o horário interno do JARVIS
        a cada 5 minutos.
        """

        while self.executando:

            self.hora_atual = datetime.now()

            print(
                "[JARVIS SINC]: "
                "Hora da memória atualizada: "
                f"{self.hora_atual.strftime('%d/%m/%Y %H:%M:%S')}"
            )

            time.sleep(300)

    # =========================================================
    # VERIFICAÇÃO AUTOMÁTICA DOS LEMBRETES
    # =========================================================

    def _loop_verificacao_lembretes(self):

        """
        Verifica continuamente se algum lembrete
        chegou ao horário programado.

        A verificação ocorre a cada 1 segundo.
        """

        while self.executando:

            try:

                lembretes = self.verificar_lembretes_pendentes()

                for lembrete in lembretes:

                    lembrete_id = lembrete[0]

                    descricao = lembrete[1]

                    horario = lembrete[2]

                    print()
                    print("=" * 50)
                    print("🔔 J.A.R.V.I.S — LEMBRETE")
                    print("=" * 50)

                    print(
                        f"📌 {descricao}"
                    )

                    print(
                        "⏰ Horário: "
                        f"{horario.strftime('%d/%m/%Y %H:%M')}"
                    )

                    print("=" * 50)
                    print()

                    self.concluir_lembrete(lembrete_id)

            except Exception as erro:

                print(
                    "[JARVIS ERRO]: "
                    f"Falha ao verificar lembretes: {erro}"
                )

            time.sleep(1)

    # =========================================================
    # ADICIONAR LEMBRETE
    # =========================================================

    def adicionar_lembrete(
        self,
        descricao: str,
        data_hora: datetime
    ) -> str:

        """Adiciona um novo lembrete ao banco."""

        query = """
        INSERT INTO lembretes
        (descricao, horario)
        VALUES (%s, %s)
        """

        conn = self._conectar()

        cursor = conn.cursor()

        cursor.execute(
            query,
            (
                descricao,
                data_hora
            )
        )

        conn.commit()

        cursor.close()

        conn.close()

        return (
            f"Lembrete '{descricao}' "
            f"agendado para "
            f"{data_hora.strftime('%d/%m/%Y às %H:%M')} "
            "com sucesso."
        )

    # =========================================================
    # VERIFICAR LEMBRETES PENDENTES
    # =========================================================

    def verificar_lembretes_pendentes(self) -> list:

        """
        Busca todos os lembretes cujo horário
        já chegou e que ainda estão pendentes.
        """

        query = """
        SELECT
            id,
            descricao,
            horario

        FROM lembretes

        WHERE
            horario <= %s
            AND status = 'pendente'
        """

        conn = self._conectar()

        cursor = conn.cursor()

        cursor.execute(
            query,
            (datetime.now(),)
        )

        resultados = cursor.fetchall()

        cursor.close()

        conn.close()

        return resultados

    # =========================================================
    # CONCLUIR LEMBRETE
    # =========================================================

    def concluir_lembrete(
        self,
        lembrete_id: int
    ):

        """Marca o lembrete como concluído."""

        query = """
        UPDATE lembretes

        SET status = 'concluido'

        WHERE id = %s
        """

        conn = self._conectar()

        cursor = conn.cursor()

        cursor.execute(
            query,
            (lembrete_id,)
        )

        conn.commit()

        cursor.close()

        conn.close()

    # =========================================================
    # CONSULTAR PALAVRA NO CÉREBRO LINGUÍSTICO
    # =========================================================

    def buscar_palavra(
        self,
        palavra: str
    ):

        """
        Consulta uma palavra no cérebro linguístico.

        Retorna:
        - forma
        - lema
        - classe gramatical
        - características morfológicas
        """

        query = """
        SELECT

            p.forma,

            p.lema,

            c.nome_portugues,

            p.caracteristicas_morfologicas

        FROM palavras p

        INNER JOIN classes_gramaticais c
            ON c.id = p.classe_id

        WHERE
            LOWER(p.forma) = LOWER(%s)

        LIMIT 1
        """

        conn = self._conectar()

        cursor = conn.cursor()

        cursor.execute(
            query,
            (palavra,)
        )

        resultado = cursor.fetchone()

        cursor.close()

        conn.close()

        return resultado

    # =========================================================
    # BUSCAR LEMA
    # =========================================================

    def buscar_lema(
        self,
        palavra: str
    ) -> str:

        """Retorna o lema de uma palavra."""

        resultado = self.buscar_palavra(palavra)

        if resultado:

            return resultado[1]

        return palavra

    # =========================================================
    # ENCERRAR MEMÓRIA
    # =========================================================

    def encerrar(self):

        """
        Encerra as threads da memória.
        """

        self.executando = False

        print(
            "[JARVIS]: "
            "Memória encerrada."
        )


# =============================================================
# TESTE DO MÓDULO
# =============================================================

if __name__ == "__main__":

    memoria = MemoriaJarvis()

    print()
    print("=" * 50)
    print("       J.A.R.V.I.S — MEMÓRIA")
    print("=" * 50)
    print()

    # ---------------------------------------------------------
    # TESTE DO HORÁRIO
    # ---------------------------------------------------------

    print(
        "Horário atual:",
        memoria.hora_atual.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    # ---------------------------------------------------------
    # TESTE DO LEMBRETE
    # ---------------------------------------------------------

    hora_lembrete = (
        datetime.now()
        + timedelta(minutes=1)
    )

    status = memoria.adicionar_lembrete(
        "Teste do sistema de lembretes",
        hora_lembrete
    )

    print(status)

    # ---------------------------------------------------------
    # TESTE DO CÉREBRO LINGUÍSTICO
    # ---------------------------------------------------------

    palavra_teste = "estudaram"

    resultado = memoria.buscar_palavra(
        palavra_teste
    )

    if resultado:

        print()
        print("CÉREBRO LINGUÍSTICO")
        print("-" * 40)

        print(
            "Forma:",
            resultado[0]
        )

        print(
            "Lema:",
            resultado[1]
        )

        print(
            "Classe:",
            resultado[2]
        )

        print(
            "Características:",
            resultado[3]
        )

    else:

        print(
            f"Palavra '{palavra_teste}' "
            "não encontrada."
        )

    # ---------------------------------------------------------
    # MANTÉM O PROGRAMA EXECUTANDO
    # ---------------------------------------------------------

    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print(
            "[JARVIS]: "
            "Encerrando..."
        )

        memoria.encerrar()

