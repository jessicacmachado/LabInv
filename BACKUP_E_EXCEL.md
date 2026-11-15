# Alteração: backups e planilha Excel do LabInv

## O que foi adicionado

Foi criada uma nova página Streamlit em `pages/2_Backup_e_Excel.py`. O Streamlit detecta a pasta `pages/` e mostra essa tela como uma página adicional no menu do aplicativo. O `app.py` original e as telas existentes não precisam ser substituídos.

A página:

1. mostra um aviso para não confiar em uma pasta temporária;
2. verifica/cria um backup automático mensal quando a página é aberta;
3. mantém até 12 arquivos de backup por ano na pasta local do servidor;
4. permite baixar uma cópia do banco `.db` pelo navegador;
5. permite baixar um Excel `.xlsx` com o inventário atual e o histórico do ano escolhido.

## Atenção sobre a pasta temporária e a nuvem

O backup automático é salvo no servidor onde o Streamlit está executando, em `~/LabInv_Backups/<ano>`. Se o serviço de hospedagem apagar arquivos locais, esse backup também pode ser apagado. A pasta do servidor **não é** automaticamente o pendrive, computador ou Google Drive/OneDrive do usuário.

Por isso, depois de baixar o `.db` ou `.xlsx`, salve o arquivo em um pendrive ou em uma pasta do seu computador sincronizada com um serviço de nuvem. A página não consegue gravar diretamente no pendrive ou na pasta pessoal do visitante por causa das regras de segurança do navegador.

## Como instalar a dependência

No terminal, dentro da pasta do projeto, execute:

```bash
pip install -r requirements.txt
```

O arquivo `requirements.txt` agora inclui `openpyxl`, biblioteca que o pandas usa para criar arquivos Excel `.xlsx`.

## Blocos e comandos identificados no código

No arquivo `pages/2_Backup_e_Excel.py`, os comentários `BLOCO 1` a `BLOCO 8` explicam a finalidade de cada parte:

- **BLOCO 1:** imports e caminhos/limites configuráveis.
- **BLOCO 2 — `ler_tabela`:** usa `sqlite3.connect` para abrir o banco e `pandas.read_sql_query` para ler uma tabela.
- **BLOCO 3 — `copiar_banco`:** cria uma cópia consistente com a API de backup do SQLite.
- **BLOCO 4 — `backup_mensal`:** cria uma cópia automática no máximo uma vez por mês quando a página é visitada e remove arquivos antigos caso ultrapassem 12 backups no ano.
- **BLOCO 5 — `gerar_excel`:** filtra o histórico pelo ano selecionado e cria duas abas no Excel: `Reagentes` e `Histórico <ano>`.
- **BLOCO 6:** apresenta aviso e verifica se o banco está disponível.
- **BLOCO 7 — `st.download_button`:** entrega uma cópia `.db` para o navegador baixar.
- **BLOCO 8 — `st.download_button`:** entrega a planilha anual `.xlsx`.

### Comandos principais, em linguagem simples

- `Path.cwd()`: encontra a pasta de onde o aplicativo foi iniciado.
- `sqlite3.connect(...)`: abre uma conexão com um arquivo SQLite.
- `origem.backup(copia)`: copia os dados do banco de forma segura.
- `pd.read_sql_query(...)`: transforma o resultado de uma consulta SQL em tabela do pandas.
- `pd.ExcelWriter(...)`: cria o arquivo Excel e suas abas.
- `DataFrame.to_excel(...)`: escreve os dados de uma tabela em uma aba da planilha.
- `st.warning(...)`: mostra o aviso sobre os arquivos temporários.
- `st.download_button(...)`: cria um botão para baixar um arquivo pelo navegador.
- `MAX_BACKUPS_PER_YEAR = 12`: configura o limite anual de cópias automáticas mantidas.

## Observação sobre a periodicidade

O backup automático é verificado quando alguém abre a página pelo menos uma vez no mês. Não é um agendador em segundo plano: se o aplicativo não for acessado no mês, não haverá uma nova cópia mensal. O botão de download manual continua disponível para baixar o banco quando necessário.
