# ==============================================================
# PROGRAMA: CONTROLE DE ESTOQUE DE REAGENTES QUÍMICOS
# Baseado nos conceitos de "Python para Todos"
# Utilizando Herança, Polimorfismo e Banco de Dados SQLite
# ==============================================================

# ==============================================================
# BLOCO 0: IMPORTAÇÕES E CONFIGURAÇÕES
# ==============================================================

import sqlite3


# ==============================================================
# BLOCO 1: CLASSES — HERANÇA E POLIMORFISMO
# ==============================================================

# CLASSE PRINCIPAL
# Representa um reagente de maneira geral.

class Reagente:

    def __init__(self, nome, quantidade):
        self.nome = nome
        self.quantidade = quantidade

    def exibir_detalhes(self):
        print(f"{self.nome}")
        print(f"    → Quantidade disponível: {self.quantidade}")


# CLASSE FILHA 1
# Representa os reagentes que já vêm na lista inicial.
# Herda os atributos e métodos da classe Reagente.

class ReagenteBasico(Reagente):

    def exibir_detalhes(self):
        print(f"{self.nome} [Reagente básico]")
        print(f"    → Quantidade disponível: {self.quantidade}")


# CLASSE FILHA 2
# Representa os reagentes cadastrados pelo usuário.
# Também herda os atributos e métodos da classe Reagente.

class ReagentePersonalizado(Reagente):

    def exibir_detalhes(self):
        print(f"{self.nome} [Reagente personalizado]")
        print(f"    → Quantidade disponível: {self.quantidade}")


# ==============================================================
# BLOCO 2: BANCO DE DADOS — CONEXÃO E CRIAÇÃO
# ==============================================================

class BancoEstoque:

    def __init__(self):
        # Cria ou abre o arquivo do banco de dados.
        self.conexao = sqlite3.connect("estoque_reagentes.db")

        # Permite acessar os dados pelo nome das colunas.
        self.conexao.row_factory = sqlite3.Row

        # Cria a tabela caso ela ainda não exista.
        self.conexao.execute("""
            CREATE TABLE IF NOT EXISTS reagentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                quantidade REAL NOT NULL,
                tipo TEXT NOT NULL
            )
        """)

        self.conexao.commit()

    # ----------------------------------------------------------
    # Inicializa os reagentes básicos sem apagar dados anteriores.
    # ----------------------------------------------------------

    def inicializar_estoque(self, lista_reagentes):

        for nome in lista_reagentes:

            self.conexao.execute("""
                INSERT OR IGNORE INTO reagentes
                (nome, quantidade, tipo)
                VALUES (?, ?, ?)
            """, (nome, 2, "basico"))

        self.conexao.commit()

    # ----------------------------------------------------------
    # Retorna todos os reagentes cadastrados no banco.
    # ----------------------------------------------------------

    def listar_reagentes(self):

        cursor = self.conexao.execute("""
            SELECT nome, quantidade, tipo
            FROM reagentes
            ORDER BY id
        """)

        return cursor.fetchall()

    # ----------------------------------------------------------
    # Busca reagentes utilizando apenas parte do nome.
    # ----------------------------------------------------------

    def buscar_reagente(self, parte_nome):

        cursor = self.conexao.execute("""
            SELECT nome
            FROM reagentes
            WHERE nome LIKE ?
            ORDER BY id
        """, (f"%{parte_nome}%",))

        return [linha["nome"] for linha in cursor.fetchall()]

    # ----------------------------------------------------------
    # Retorna os dados de um reagente específico.
    # ----------------------------------------------------------

    def obter_reagente(self, nome):

        cursor = self.conexao.execute("""
            SELECT nome, quantidade, tipo
            FROM reagentes
            WHERE nome = ?
        """, (nome,))

        return cursor.fetchone()

    # ----------------------------------------------------------
    # Atualiza a quantidade de um reagente.
    # ----------------------------------------------------------

    def atualizar_quantidade(self, nome, quantidade):

        self.conexao.execute("""
            UPDATE reagentes
            SET quantidade = ?
            WHERE nome = ?
        """, (quantidade, nome))

        self.conexao.commit()

    # ----------------------------------------------------------
    # Cadastra um reagente personalizado.
    # ----------------------------------------------------------

    def cadastrar_reagente(self, nome):

        self.conexao.execute("""
            INSERT INTO reagentes
            (nome, quantidade, tipo)
            VALUES (?, ?, ?)
        """, (nome, 2, "personalizado"))

        self.conexao.commit()

    # ----------------------------------------------------------
    # Encerra a conexão com o banco de dados.
    # ----------------------------------------------------------

    def fechar(self):
        self.conexao.close()


# ==============================================================
# BLOCO 3: DADOS INICIAIS — LISTA DE REAGENTES
# ==============================================================

reagentes_basicos = [

    "1. Ácido Clorídrico (HCl)",
    "2. Ácido Sulfúrico (H2SO4)",
    "3. Ácido Nítrico (HNO3)",
    "4. Ácido Acético (CH3COOH)",
    "5. Hidróxido de Sódio (NaOH)",
    "6. Hidróxido de Amônio (NH4OH)",
    "7. Hidróxido de Cálcio (Ca(OH)2)",
    "8. Bicarbonato de Sódio (NaHCO3)",
    "9. Cloreto de Sódio (NaCl)",
    "10. Sulfato de Cobre II (CuSO4)",
    "11. Nitrato de Prata (AgNO3)",
    "12. Cloreto de Bário (BaCl2)",
    "13. Carbonato de Sódio (Na2CO3)",
    "14. Permanganato de Potássio (KMnO4)",
    "15. Iodeto de Potássio (KI)",
    "16. Cromato de Potássio (K2CrO4)",
    "17. Água Destilada/Deionizada (H2O)",
    "18. Álcool Etílico/Etanol (C2H5OH)",
    "19. Acetona (CH3COCH3)",
    "20. Hexano (C6H14)",
    "21. Fenolftaleína",
    "22. Metiloranje (Alaranjado de Metila)",
    "23. Azul de Bromotimol",
    "24. Solução de Amido",
    "25. Peróxido de Hidrogênio (H2O2)",
    "26. Glicerina/Glicerol",
    "27. Ácido Ascórbico",
    "28. Sulfato de Magnésio (MgSO4) Anidro",
    "29. Glicose (C6H12O6)",
    "30. Nitrato de Amônio (NH4NO3)"

]


# ==============================================================
# BLOCO 4: TELA DE ABERTURA — MENSAGEM DE BOAS-VINDAS
# ==============================================================

def tela_boas_vindas():

    print("\n\n")

    print("🔬 " + "="*54 + " 🔬")
    print("🧪           Bem-vindo ao LabInv 🧪")
    print("🔬 " + "="*54 + " 🔬")

    print("\n")

    print("   Sistema de Controle de Estoque de Reagentes Químicos")
    print("   Laboratório de Investigação")

    print("\n")

    print("   Carregando lista de reagentes...")
    print("   Verificando banco de dados...")
    print("   Pronto! Sistema ativo.")

    print("\n" + "-"*58)

    input("   Pressione ENTER para acessar o sistema...")

    print("\n" * 3)


# ==============================================================
# BLOCO 5: FUNÇÃO — MOSTRAR LISTA COMPLETA
# ==============================================================

def mostrar_lista(banco):

    print("\n" + "="*60)
    print("             LISTA DE REAGENTES CADASTRADOS")
    print("="*60)

    # Busca todos os reagentes no banco de dados.
    resultados = banco.listar_reagentes()

    for item in resultados:

        # Verifica o tipo do reagente e cria o objeto correspondente.
        if item["tipo"] == "basico":

            reagente = ReagenteBasico(
                item["nome"],
                item["quantidade"]
            )

        else:

            reagente = ReagentePersonalizado(
                item["nome"],
                item["quantidade"]
            )

        # POLIMORFISMO:
        # O mesmo método funciona de maneira diferente
        # dependendo da classe do objeto.
        reagente.exibir_detalhes()

        print("-" * 60)

    print("="*60)
    print(f"Total de reagentes cadastrados: {len(resultados)}")
    print("="*60)


# ==============================================================
# BLOCO 6: FUNÇÃO — BUSCAR REAGENTE
# ==============================================================

def buscar_reagente(banco, parte_nome):

    # A busca agora é realizada diretamente no banco de dados.
    encontrados = banco.buscar_reagente(parte_nome)

    return encontrados


# ==============================================================
# BLOCO 7: FUNÇÃO — SELECIONAR REAGENTE
# ==============================================================

def selecionar_reagente(resultados):

    if len(resultados) == 1:

        print(f"✅ Reagente encontrado: {resultados[0]}")

        return resultados[0]

    print("\n⚠️ Encontrados vários reagentes:")

    for indice, nome in enumerate(resultados):

        print(f"   {indice + 1} - {nome}")

    escolha = input("Digite o número do reagente desejado: ")

    try:

        numero = int(escolha) - 1

        if 0 <= numero < len(resultados):

            return resultados[numero]

        else:

            print("❌ Número fora do intervalo!")

            return None

    except ValueError:

        print("❌ Digite um número válido!")

        return None


# ==============================================================
# BLOCO 8: FUNÇÃO — RETIRADA DE REAGENTE
# ==============================================================

def retirar_reagente(banco):

    print("\n" + "-"*45)
    print("         RETIRADA DE REAGENTE")
    print("-"*45)

    palavra_chave = input("Digite o nome ou parte do nome: ")

    lista_encontrada = buscar_reagente(banco, palavra_chave)

    if len(lista_encontrada) == 0:

        print("❌ Reagente não cadastrado!")

        return

    reagente_escolhido = selecionar_reagente(lista_encontrada)

    if reagente_escolhido is None:

        return

    texto_qtd = input("Digite a quantidade a ser retirada: ")

    try:

        qtd = float(texto_qtd)

        if qtd <= 0:

            print("❌ A quantidade deve ser maior que zero!")

            return

        # Consulta a quantidade atual no banco de dados.
        reagente = banco.obter_reagente(reagente_escolhido)

        if reagente["quantidade"] >= qtd:

            nova_quantidade = reagente["quantidade"] - qtd

            # Salva a nova quantidade no banco.
            banco.atualizar_quantidade(
                reagente_escolhido,
                nova_quantidade
            )

            print("✅ Retirada realizada!")
            print(f"   Quantidade restante: {nova_quantidade}")

        else:

            print(
                f"❌ Estoque insuficiente! "
                f"Disponível: {reagente['quantidade']}"
            )

    except ValueError:

        print("❌ Digite um número válido!")


# ==============================================================
# BLOCO 9: FUNÇÃO — DEVOLUÇÃO DE REAGENTE
# ==============================================================

def devolver_reagente(banco):

    print("\n" + "-"*45)
    print("        DEVOLUÇÃO DE REAGENTE")
    print("-"*45)

    palavra_chave = input("Digite o nome ou parte do nome: ")

    lista_encontrada = buscar_reagente(banco, palavra_chave)

    if len(lista_encontrada) == 0:

        print("❌ Reagente não cadastrado!")

        return

    reagente_escolhido = selecionar_reagente(lista_encontrada)

    if reagente_escolhido is None:

        return

    texto_qtd = input("Digite a quantidade devolvida: ")

    try:

        qtd = float(texto_qtd)

        if qtd <= 0:

            print("❌ A quantidade deve ser maior que zero!")

            return

        # Consulta a quantidade atual.
        reagente = banco.obter_reagente(reagente_escolhido)

        nova_quantidade = reagente["quantidade"] + qtd

        # Atualiza o banco de dados.
        banco.atualizar_quantidade(
            reagente_escolhido,
            nova_quantidade
        )

        print("✅ Devolução realizada!")
        print(f"   Nova quantidade: {nova_quantidade}")

    except ValueError:

        print("❌ Digite um número válido!")


# ==============================================================
# BLOCO 10: FUNÇÃO — CADASTRAR NOVO REAGENTE
# ==============================================================

def cadastrar_novo(banco):

    print("\n" + "-"*45)
    print("       CADASTRO DE NOVO REAGENTE")
    print("-"*45)

    nome_novo = input("Digite o nome e fórmula do reagente: ").strip()

    if not nome_novo:

        print("❌ O nome não pode ficar vazio!")

        return

    # Verifica se já existe um reagente com o mesmo nome.
    if banco.obter_reagente(nome_novo) is not None:

        print("⚠️ Esse reagente já está cadastrado!")

        return

    try:

        # Cadastra no banco com quantidade inicial de 2.
        banco.cadastrar_reagente(nome_novo)

        print(f"✅ Cadastrado com sucesso: {nome_novo}")
        print("   Quantidade inicial: 2 unidades")

    except sqlite3.IntegrityError:

        print("❌ Não foi possível cadastrar o reagente!")


# ==============================================================
# BLOCO 11: PROGRAMA PRINCIPAL — INÍCIO DO SISTEMA
# ==============================================================

# Cria ou conecta ao banco de dados.
banco = BancoEstoque()

# Adiciona os 30 reagentes iniciais apenas se ainda não existirem.
banco.inicializar_estoque(reagentes_basicos)

# Exibe a tela de abertura.
tela_boas_vindas()

while True:

    print("\n" + "~"*45)
    print("             MENU DE OPÇÕES")
    print("~"*45)

    print("  1 → Ver todos os reagentes cadastrados")
    print("  2 → Retirar reagente do estoque")
    print("  3 → Devolver/repor reagente no estoque")
    print("  4 → Cadastrar novo reagente")
    print("  5 → Sair do sistema")

    print("~"*45)

    opcao_escolhida = input("Escolha uma opção (1 a 5): ")

    if opcao_escolhida == "1":

        mostrar_lista(banco)

    elif opcao_escolhida == "2":

        retirar_reagente(banco)

    elif opcao_escolhida == "3":

        devolver_reagente(banco)

    elif opcao_escolhida == "4":

        cadastrar_novo(banco)

    elif opcao_escolhida == "5":

        print("\n👋 Encerrando o sistema... Até logo!")

        break

    else:

        print("❌ Opção inválida! Escolha entre 1 e 5.")


# Fecha a conexão após sair do menu.
banco.fechar()

