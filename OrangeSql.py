import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# ==================== ENUMS ====================
class Status(Enum):
    """Enum para status de tarefas e etapas"""
    NAO_INICIADA = "não iniciada"
    EM_ANDAMENTO = "em andamento"
    CONCLUIDO = "concluído"

# ==================== DATACLASSES ====================
@dataclass
class Usuario:
    """Representa um usuário do sistema"""
    id: int
    nome: str
    senha: str
    data_criacao: str

@dataclass
class LogAcao:
    """Representa um log de ação realizada"""
    id: int
    usuario_id: int
    acao: str
    entidade: str
    entidade_id: int
    detalhes: str
    data_hora: str

@dataclass
class Pessoa:
    """Representa uma pessoa responsável"""
    id: int
    nome: str
    email: Optional[str] = None

@dataclass
class Etapa:
    """Representa uma etapa de uma tarefa"""
    id: int
    tarefa_id: int
    nome: str
    descricao: Optional[str]
    status: Status
    pessoa_encarregada_id: Optional[int]
    data_criacao: str
    
class Tarefa:
    """Representa uma tarefa dentro de um eixo"""
    _id_counter = 1  # Singleton para geração IDs
    
    def __init__(self, eixo_id: int, nome: str, 
                 prioridade: int, status: Status = Status.NAO_INICIADA):
        self.id = Tarefa._id_counter
        Tarefa._id_counter += 1
        self.eixo_id = eixo_id
        self.nome = nome
        self.prioridade = prioridade  # 1-5
        self.status = status
        self.encarregados: List[Pessoa] = []
        self.etapas: List[Etapa] = []
        self.data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def adicionar_encarregado(self, pessoa: Pessoa):
        """Adiciona uma pessoa responsável à tarefa"""
        if pessoa not in self.encarregados:
            self.encarregados.append(pessoa)
    
    def remover_encarregado(self, pessoa: Pessoa):
        """Remove uma pessoa responsável da tarefa"""
        if pessoa in self.encarregados:
            self.encarregados.remove(pessoa)

@dataclass
class Eixo:
    """Representa um eixo contendo tarefas"""
    id: int
    nome: str
    descricao: Optional[str] = None
    data_criacao: str = None
    
    def __post_init__(self):
        if self.data_criacao is None:
            self.data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==================== BANCO DE DADOS ====================
class BancoDadosSQLite:
    """Gerencia a conexão e operações com SQLite"""
    
    def __init__(self, nome_banco: str = "gerenciador_atividades.db"):
        self.nome_banco = nome_banco
        self.conexao = None
        self.cursor = None
        self.inicializar_banco()
    
    def inicializar_banco(self):
        """Cria a conexão e define as tabelas"""
        self.conexao = sqlite3.connect(self.nome_banco)
        self.cursor = self.conexao.cursor()
        self.criar_tabelas()
    
    def criar_tabelas(self):
        """Cria as tabelas necessárias"""
        # Tabela de usuários
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                senha TEXT NOT NULL,
                data_criacao TEXT
            )
        ''')
        
        # Tabela de logs de ações
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs_acoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                acao TEXT NOT NULL,
                entidade TEXT NOT NULL,
                entidade_id INTEGER NOT NULL,
                detalhes TEXT,
                data_hora TEXT,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        
        # Tabela de pessoas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pessoas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT
            )
        ''')
        
        # Tabela de eixos
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS eixos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                data_criacao TEXT
            )
        ''')
        
        # Tabela de tarefas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eixo_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                prioridade INTEGER,
                status TEXT,
                data_criacao TEXT,
                FOREIGN KEY(eixo_id) REFERENCES eixos(id)
            )
        ''')
        
        # Tabela de associação tarefa-pessoa (encarregados)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tarefa_encarregados (
                tarefa_id INTEGER,
                pessoa_id INTEGER,
                PRIMARY KEY (tarefa_id, pessoa_id),
                FOREIGN KEY(tarefa_id) REFERENCES tarefas(id),
                FOREIGN KEY(pessoa_id) REFERENCES pessoas(id)
            )
        ''')
        
        # Tabela de etapas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS etapas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarefa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                descricao TEXT,
                status TEXT,
                pessoa_encarregada_id INTEGER,
                data_criacao TEXT,
                FOREIGN KEY(tarefa_id) REFERENCES tarefas(id),
                FOREIGN KEY(pessoa_encarregada_id) REFERENCES pessoas(id)
            )
        ''')
        
        self.conexao.commit()
    
    def adicionar_pessoa(self, nome: str, email: Optional[str] = None, usuario_id: int = None) -> int:
        """Adiciona uma pessoa ao banco de dados"""
        self.cursor.execute('INSERT INTO pessoas (nome, email) VALUES (?, ?)', (nome, email))
        pessoa_id = self.cursor.lastrowid
        self.conexao.commit()
        
        # Registrar ação no log
        if usuario_id:
            self.registrar_acao(
                usuario_id, 
                "CRIAR", 
                "PESSOA", 
                pessoa_id, 
                f"Pessoa '{nome}' adicionada"
            )
        
        return pessoa_id
    
    def adicionar_eixo(self, nome: str, descricao: Optional[str] = None, usuario_id: int = None) -> int:
        """Adiciona um eixo ao banco de dados"""
        data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            'INSERT INTO eixos (nome, descricao, data_criacao) VALUES (?, ?, ?)',
            (nome, descricao, data_criacao)
        )
        eixo_id = self.cursor.lastrowid
        self.conexao.commit()
        
        # Registrar ação no log
        if usuario_id:
            self.registrar_acao(
                usuario_id, 
                "CRIAR", 
                "EIXO", 
                eixo_id, 
                f"Eixo '{nome}' criado"
            )
        
        return eixo_id
    
    def obter_eixos(self) -> List[Eixo]:
        """Obtém todos os eixos do banco de dados"""
        self.cursor.execute('SELECT id, nome, descricao, data_criacao FROM eixos')
        eixos = []
        for row in self.cursor.fetchall():
            eixos.append(Eixo(id=row[0], nome=row[1], descricao=row[2], data_criacao=row[3]))
        return eixos
    
    def obter_pessoas(self) -> List[Pessoa]:
        """Obtém todas as pessoas do banco de dados"""
        self.cursor.execute('SELECT id, nome, email FROM pessoas')
        pessoas = []
        for row in self.cursor.fetchall():
            pessoas.append(Pessoa(id=row[0], nome=row[1], email=row[2]))
        return pessoas
    
    # ========== MÉTODOS DE USUÁRIOS ==========
    def criar_usuario_padrao(self):
        """Cria o usuário padrão 'Pedro' se não existir"""
        self.cursor.execute('SELECT COUNT(*) FROM usuarios WHERE nome = ?', ('Pedro',))
        if self.cursor.fetchone()[0] == 0:
            data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'INSERT INTO usuarios (nome, senha, data_criacao) VALUES (?, ?, ?)',
                ('Pedro', '123', data_criacao)
            )
            self.conexao.commit()
    
    def verificar_login(self, nome: str, senha: str) -> Optional[Usuario]:
        self.cursor.execute(
            'SELECT id, nome, senha, data_criacao FROM usuarios WHERE nome = ? AND senha = ?',
            (nome, senha)
        )
        row = self.cursor.fetchone()
        if row:
            return Usuario(id=row[0], nome=row[1], senha=row[2], data_criacao=row[3])
        return None
    
    def obter_usuario_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """FETCH BY ID"""
        self.cursor.execute('SELECT id, nome, senha, data_criacao FROM usuarios WHERE id = ?', (usuario_id,))
        row = self.cursor.fetchone()
        if row:
            return Usuario(id=row[0], nome=row[1], senha=row[2], data_criacao=row[3])
        return None
    
    # ========== MÉTODOS DE LOGS ==========
    def registrar_acao(self, usuario_id: int, acao: str, entidade: str, entidade_id: int, detalhes: str = ""):
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO logs_acoes (usuario_id, acao, entidade, entidade_id, detalhes, data_hora)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (usuario_id, acao, entidade, entidade_id, detalhes, data_hora))
        self.conexao.commit()
    
    def obter_logs_usuario(self, usuario_id: int) -> List[LogAcao]:
        """Obtém todos os logs de ações de um usuário"""
        self.cursor.execute('''
            SELECT id, usuario_id, acao, entidade, entidade_id, detalhes, data_hora
            FROM logs_acoes
            WHERE usuario_id = ?
            ORDER BY data_hora DESC
        ''', (usuario_id,))
        
        logs = []
        for row in self.cursor.fetchall():
            logs.append(LogAcao(
                id=row[0], usuario_id=row[1], acao=row[2], entidade=row[3],
                entidade_id=row[4], detalhes=row[5], data_hora=row[6]
            ))
        return logs
def adicionar_tarefa(banco_dados: BancoDadosSQLite, eixo_id: int, nome: str, 
                     prioridade: int, usuario_id: int,
                     status: Status = Status.NAO_INICIADA) -> int:
    
    data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    banco_dados.cursor.execute('''
        INSERT INTO tarefas (eixo_id, nome, prioridade, status, data_criacao)
        VALUES (?, ?, ?, ?, ?)
    ''', (eixo_id, nome, prioridade, status.value, data_criacao))
    
    tarefa_id = banco_dados.cursor.lastrowid
    banco_dados.conexao.commit()
    
    # Registrar ação no log
    banco_dados.registrar_acao(
        usuario_id, 
        "CRIAR", 
        "TAREFA", 
        tarefa_id, 
        f"Tarefa '{nome}' criada no eixo {eixo_id} com prioridade {prioridade}"
    )
    
    return tarefa_id

def adicionar_etapa(banco_dados: BancoDadosSQLite, tarefa_id: int, nome: str,
                    descricao: Optional[str] = None, 
                    pessoa_encarregada_id: Optional[int] = None,
                    usuario_id: int = None,
                    status: Status = Status.NAO_INICIADA) -> int:
    """
    Adiciona uma nova etapa a uma tarefa
    
    Args:
        banco_dados: Instância do banco de dados
        tarefa_id: ID da tarefa ao qual a etapa será adicionada
        nome: Nome da etapa
        descricao: Descrição da etapa (opcional)
        pessoa_encarregada_id: ID da pessoa responsável (opcional)
        usuario_id: ID do usuário que está criando a etapa
        status: Status inicial da etapa (padrão: não iniciada)
    
    Returns:
        ID da etapa criada
    """
    data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    banco_dados.cursor.execute('''
        INSERT INTO etapas (tarefa_id, nome, descricao, status, pessoa_encarregada_id, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (tarefa_id, nome, descricao, status.value, pessoa_encarregada_id, data_criacao))
    
    etapa_id = banco_dados.cursor.lastrowid
    banco_dados.conexao.commit()
    
    # Registrar ação no log
    if usuario_id:
        banco_dados.registrar_acao(
            usuario_id, 
            "CRIAR", 
            "ETAPA", 
            etapa_id, 
            f"Etapa '{nome}' criada na tarefa {tarefa_id}"
        )
    
    return etapa_id

# ==================== INTERFACE TKINTER ====================
class TelaLogin:
    """Tela de login do sistema"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Login - OrangeSQL")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        self.banco_dados = BancoDadosSQLite()
        self.usuario_logado = None
        
        # Centralizar a janela
        self.root.eval('tk::PlaceWindow . center')
        
        self.setup_interface()
    
    def setup_interface(self):
        """Configura a interface de login"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        titulo_label = ttk.Label(
            main_frame, 
            text="OrangeSQL", 
            font=("Arial", 20, "bold"),
            foreground="#FF6B35"
        )
        titulo_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        subtitulo_label = ttk.Label(
            main_frame, 
            text="Sistema de Gerenciamento de Atividades", 
            font=("Arial", 10)
        )
        subtitulo_label.grid(row=1, column=0, columnspan=2, pady=(0, 30))
        
        # Campo usuário
        ttk.Label(main_frame, text="Usuário:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_usuario = ttk.Entry(main_frame, width=30, font=("Arial", 10))
        self.entry_usuario.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        self.entry_usuario.insert(0, "Pedro")  # Usuário padrão
        
        # Campo senha
        ttk.Label(main_frame, text="Senha:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.entry_senha = ttk.Entry(main_frame, width=30, font=("Arial", 10), show="*")
        self.entry_senha.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        self.entry_senha.insert(0, "123")  # Senha padrão
        
        # Botão login
        self.btn_login = ttk.Button(
            main_frame, 
            text="Entrar", 
            command=self.fazer_login,
            width=20
        )
        self.btn_login.grid(row=4, column=0, columnspan=2, pady=20)
        
        # Label para mensagens
        self.label_mensagem = ttk.Label(main_frame, text="", font=("Arial", 9), foreground="red")
        self.label_mensagem.grid(row=5, column=0, columnspan=2, pady=5)
        
        # Configurar foco
        self.entry_usuario.focus()
        
        # Bind para Enter
        self.root.bind('<Return>', lambda e: self.fazer_login())
    
    def fazer_login(self):
        """Processa o login"""
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get().strip()
        
        if not usuario or not senha:
            self.label_mensagem.config(text="Preencha usuário e senha!", foreground="red")
            return
        
        usuario_logado = self.banco_dados.verificar_login(usuario, senha)
        
        if usuario_logado:
            self.usuario_logado = usuario_logado
            self.label_mensagem.config(text="Login realizado com sucesso!", foreground="green")
            self.root.after(1000, self.abrir_menu_principal)
        else:
            self.label_mensagem.config(text="Usuário ou senha incorretos!", foreground="red")
    
    def abrir_menu_principal(self):
        """Abre o menu principal após login"""
        self.root.destroy()  # Fecha tela de login
        
        # Abre menu principal
        root_principal = tk.Tk()
        app = MenuPrincipal(root_principal, self.usuario_logado)
        root_principal.mainloop()

class MenuPrincipal:
    """Menu principal com opções Editar Projeto e Visualizar Projeto"""
    
    def __init__(self, root, usuario):
        self.root = root
        self.usuario = usuario
        self.root.title(f"OrangeSQL - Bem-vindo, {usuario.nome}")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Centralizar a janela
        self.root.eval('tk::PlaceWindow . center')
        
        self.setup_interface()
    
    def setup_interface(self):
        """Configura a interface do menu principal"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        titulo_label = ttk.Label(
            main_frame, 
            text="OrangeSQL", 
            font=("Arial", 24, "bold"),
            foreground="#FF6B35"
        )
        titulo_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        subtitulo_label = ttk.Label(
            main_frame, 
            text=f"Bem-vindo, {self.usuario.nome}!", 
            font=("Arial", 12)
        )
        subtitulo_label.grid(row=1, column=0, columnspan=2, pady=(0, 40))
        
        # Botões principais
        btn_editar = ttk.Button(
            main_frame,
            text="📝 Editar Projeto",
            command=self.abrir_editar_projeto,
            width=25
        )
        btn_editar.grid(row=2, column=0, padx=20, pady=20, ipadx=20, ipady=15)
        
        btn_visualizar = ttk.Button(
            main_frame,
            text="👁️ Visualizar Projeto",
            command=self.abrir_visualizar_projeto,
            width=25
        )
        btn_visualizar.grid(row=2, column=1, padx=20, pady=20, ipadx=20, ipady=15)
        
        # Botão sair
        btn_sair = ttk.Button(
            main_frame,
            text="🚪 Sair",
            command=self.sair,
            width=25
        )
        btn_sair.grid(row=3, column=0, columnspan=2, pady=30, ipadx=20, ipady=10)
    
    def abrir_editar_projeto(self):
        """Abre a tela de edição do projeto"""
        self.root.destroy()
        root_editar = tk.Tk()
        app = AplicacaoGerenciador(root_editar, self.usuario)
        root_editar.mainloop()
    
    def abrir_visualizar_projeto(self):
        """Abre a tela de visualização do projeto"""
        self.root.destroy()
        root_visualizar = tk.Tk()
        app = VisualizarProjeto(root_visualizar, self.usuario)
        root_visualizar.mainloop()
    
    def sair(self):
        """Fecha a aplicação"""
        self.root.quit()

class AplicacaoGerenciador:
    """Interface gráfica para gerenciar atividades"""
    
    def __init__(self, root, usuario):
        self.root = root
        self.usuario = usuario
        self.root.title(f"Editar Projeto - OrangeSQL ({usuario.nome})")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        
        # Configurar estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        self.banco_dados = BancoDadosSQLite()
        self.setup_interface()
    
    def setup_interface(self):
        """Configura a interface gráfica"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Abas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Aba para gerenciar eixos
        self.frame_eixos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_eixos, text="Eixos")
        self.setup_aba_eixos()
        
        # Aba para gerenciar tarefas
        self.frame_tarefas = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tarefas, text="Tarefas")
        self.setup_aba_tarefas()
        
        # Aba para gerenciar etapas
        self.frame_etapas = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_etapas, text="Etapas")
        self.setup_aba_etapas()
        
        # Aba para gerenciar pessoas
        self.frame_pessoas = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_pessoas, text="Pessoas")
        self.setup_aba_pessoas()
    
    def setup_aba_eixos(self):
        """Configurar aba de eixos com layout melhorado"""
        # Frame superior para formulário
        frame_form = ttk.LabelFrame(self.frame_eixos, text="Criar Novo Eixo", padding="15")
        frame_form.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), padx=10, pady=10)
        
        ttk.Label(frame_form, text="Nome:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.entry_eixo_nome = ttk.Entry(frame_form, width=40, font=("Arial", 10))
        self.entry_eixo_nome.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Descrição:", font=("Arial", 10)).grid(row=1, column=0, sticky=(tk.W, tk.N), pady=8)
        self.entry_eixo_descricao = ttk.Entry(frame_form, width=40, font=("Arial", 10))
        self.entry_eixo_descricao.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        frame_form.columnconfigure(1, weight=1)
        
        ttk.Button(
            frame_form, 
            text="✓ Criar Eixo", 
            command=self.adicionar_eixo_clique
        ).grid(row=2, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))
        
        # Frame inferior para listagem
        frame_lista = ttk.LabelFrame(self.frame_eixos, text="Eixos Cadastrados", padding="10")
        frame_lista.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        colunas = ("ID", "Nome", "Descrição")
        self.tree_eixos = ttk.Treeview(frame_lista, columns=colunas, height=12, show="headings")
        
        self.tree_eixos.column("ID", width=40)
        self.tree_eixos.column("Nome", width=150)
        self.tree_eixos.column("Descrição", width=300)
        
        for col in colunas:
            self.tree_eixos.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree_eixos.yview)
        self.tree_eixos.configure(yscroll=scrollbar.set)
        
        self.tree_eixos.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        frame_lista.columnconfigure(0, weight=1)
        frame_lista.rowconfigure(0, weight=1)
        
        self.frame_eixos.rowconfigure(1, weight=1)
        self.frame_eixos.columnconfigure(0, weight=1)
        
        self.atualizar_lista_eixos_tree()
    
    def setup_aba_tarefas(self):
        """Configurar aba de tarefas com layout melhorado"""
        # Frame superior para formulário
        frame_form = ttk.LabelFrame(self.frame_tarefas, text="Adicionar Nova Tarefa", padding="15")
        frame_form.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), padx=10, pady=10)
        
        ttk.Label(frame_form, text="Eixo:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.combo_eixo = ttk.Combobox(frame_form, state="readonly", width=30, font=("Arial", 10))
        self.combo_eixo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Nome da Tarefa:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.entry_tarefa_nome = ttk.Entry(frame_form, width=30, font=("Arial", 10))
        self.entry_tarefa_nome.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Prioridade:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        self.combo_prioridade = ttk.Combobox(
            frame_form, 
            values=["⭐ 1 - Baixa", "⭐⭐ 2 - Média", "⭐⭐⭐ 3 - Moderada", "⭐⭐⭐⭐ 4 - Alta", "⭐⭐⭐⭐⭐ 5 - Crítica"],
            state="readonly",
            width=30,
            font=("Arial", 10)
        )
        self.combo_prioridade.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        frame_form.columnconfigure(1, weight=1)
        
        ttk.Button(
            frame_form, 
            text="✓ Adicionar Tarefa", 
            command=self.adicionar_tarefa_clique
        ).grid(row=3, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))
        
        # Frame inferior para listagem
        frame_lista = ttk.LabelFrame(self.frame_tarefas, text="Tarefas", padding="10")
        frame_lista.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Treeview para mostrar tarefas
        colunas = ("ID", "Eixo", "Nome", "Prioridade", "Status")
        self.tree_tarefas = ttk.Treeview(frame_lista, columns=colunas, height=12, show="headings")
        
        self.tree_tarefas.column("ID", width=30)
        self.tree_tarefas.column("Eixo", width=100)
        self.tree_tarefas.column("Nome", width=250)
        self.tree_tarefas.column("Prioridade", width=80)
        self.tree_tarefas.column("Status", width=100)
        
        for col in colunas:
            self.tree_tarefas.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree_tarefas.yview)
        self.tree_tarefas.configure(yscroll=scrollbar.set)
        
        self.tree_tarefas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        frame_lista.columnconfigure(0, weight=1)
        frame_lista.rowconfigure(0, weight=1)
        
        self.frame_tarefas.rowconfigure(1, weight=1)
        self.frame_tarefas.columnconfigure(0, weight=1)
        
        self.atualizar_combo_eixos()
        self.atualizar_lista_tarefas()
    
    def setup_aba_etapas(self):
        """Configurar aba de etapas com layout melhorado"""
        # Frame superior para formulário
        frame_form = ttk.LabelFrame(self.frame_etapas, text="Adicionar Nova Etapa", padding="15")
        frame_form.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), padx=10, pady=10)
        
        ttk.Label(frame_form, text="Tarefa:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.combo_tarefa = ttk.Combobox(frame_form, state="readonly", width=30, font=("Arial", 10))
        self.combo_tarefa.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Nome da Etapa:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.entry_etapa_nome = ttk.Entry(frame_form, width=30, font=("Arial", 10))
        self.entry_etapa_nome.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Descrição:", font=("Arial", 10)).grid(row=2, column=0, sticky=(tk.W, tk.N), pady=8)
        self.entry_etapa_descricao = ttk.Entry(frame_form, width=30, font=("Arial", 10))
        self.entry_etapa_descricao.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Responsável:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=8)
        self.combo_pessoa = ttk.Combobox(frame_form, state="readonly", width=30, font=("Arial", 10))
        self.combo_pessoa.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        frame_form.columnconfigure(1, weight=1)
        
        ttk.Button(
            frame_form, 
            text="✓ Adicionar Etapa", 
            command=self.adicionar_etapa_clique
        ).grid(row=4, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))
        
        # Frame inferior para listagem
        frame_lista = ttk.LabelFrame(self.frame_etapas, text="Etapas", padding="10")
        frame_lista.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        colunas = ("ID", "Tarefa", "Nome", "Status", "Responsável")
        self.tree_etapas = ttk.Treeview(frame_lista, columns=colunas, height=12, show="headings")
        
        self.tree_etapas.column("ID", width=40)
        self.tree_etapas.column("Tarefa", width=120)
        self.tree_etapas.column("Nome", width=200)
        self.tree_etapas.column("Status", width=120)
        self.tree_etapas.column("Responsável", width=120)
        
        for col in colunas:
            self.tree_etapas.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree_etapas.yview)
        self.tree_etapas.configure(yscroll=scrollbar.set)
        
        self.tree_etapas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        frame_lista.columnconfigure(0, weight=1)
        frame_lista.rowconfigure(0, weight=1)
        
        self.frame_etapas.rowconfigure(1, weight=1)
        self.frame_etapas.columnconfigure(0, weight=1)
        
        self.atualizar_combo_tarefas()
        self.atualizar_combo_pessoas()
        self.atualizar_lista_etapas()
    
    def setup_aba_pessoas(self):
        """Configurar aba de pessoas com layout melhorado"""
        # Frame superior para formulário
        frame_form = ttk.LabelFrame(self.frame_pessoas, text="Adicionar Nova Pessoa", padding="15")
        frame_form.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), padx=10, pady=10)
        
        ttk.Label(frame_form, text="Nome:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.entry_pessoa_nome = ttk.Entry(frame_form, width=40, font=("Arial", 10))
        self.entry_pessoa_nome.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        ttk.Label(frame_form, text="Email:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.entry_pessoa_email = ttk.Entry(frame_form, width=40, font=("Arial", 10))
        self.entry_pessoa_email.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=8)
        
        frame_form.columnconfigure(1, weight=1)
        
        ttk.Button(
            frame_form, 
            text="✓ Adicionar Pessoa", 
            command=self.adicionar_pessoa_clique
        ).grid(row=2, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))
        
        # Frame inferior para listagem
        frame_lista = ttk.LabelFrame(self.frame_pessoas, text="Pessoas Cadastradas", padding="10")
        frame_lista.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        colunas = ("ID", "Nome", "Email")
        self.tree_pessoas = ttk.Treeview(frame_lista, columns=colunas, height=12, show="headings")
        
        self.tree_pessoas.column("ID", width=40)
        self.tree_pessoas.column("Nome", width=150)
        self.tree_pessoas.column("Email", width=300)
        
        for col in colunas:
            self.tree_pessoas.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree_pessoas.yview)
        self.tree_pessoas.configure(yscroll=scrollbar.set)
        
        self.tree_pessoas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        frame_lista.columnconfigure(0, weight=1)
        frame_lista.rowconfigure(0, weight=1)
        
        self.frame_pessoas.rowconfigure(1, weight=1)
        self.frame_pessoas.columnconfigure(0, weight=1)
        
        self.atualizar_lista_pessoas()
    
    # ========== Métodos de atualização ==========
    def atualizar_lista_eixos(self):
        """Atualiza a lista de eixos (depreciado)"""
        pass
    
    def atualizar_lista_eixos_tree(self):
        """Atualiza a árvore de eixos"""
        for item in self.tree_eixos.get_children():
            self.tree_eixos.delete(item)
        
        eixos = self.banco_dados.obter_eixos()
        for eixo in eixos:
            desc = eixo.descricao or ""
            self.tree_eixos.insert("", "end", values=(eixo.id, eixo.nome, desc))
    
    def atualizar_combo_eixos(self):
        """Atualiza o combobox de eixos"""
        eixos = self.banco_dados.obter_eixos()
        self.eixos_dict = {eixo.nome: eixo.id for eixo in eixos}
        self.combo_eixo['values'] = list(self.eixos_dict.keys())
    
    def atualizar_combo_tarefas(self):
        """Atualiza o combobox de tarefas"""
        self.banco_dados.cursor.execute('SELECT id, nome FROM tarefas')
        tarefas = self.banco_dados.cursor.fetchall()
        self.tarefas_dict = {f"{t[1]} (ID: {t[0]})": t[0] for t in tarefas}
        self.combo_tarefa['values'] = list(self.tarefas_dict.keys())
    
    def atualizar_lista_tarefas(self):
        """Atualiza a árvore de tarefas"""
        for item in self.tree_tarefas.get_children():
            self.tree_tarefas.delete(item)
        
        self.banco_dados.cursor.execute('''
            SELECT t.id, e.nome, t.nome, t.prioridade, t.status
            FROM tarefas t
            JOIN eixos e ON t.eixo_id = e.id
            ORDER BY t.id DESC
        ''')
        
        for row in self.banco_dados.cursor.fetchall():
            prioridade = f"⭐ {row[3]}" if row[3] else "N/A"
            self.tree_tarefas.insert("", "end", values=(row[0], row[1], row[2], prioridade, row[4]))
    
    def atualizar_combo_pessoas(self):
        """Atualiza o combobox de pessoas"""
        pessoas = self.banco_dados.obter_pessoas()
        self.pessoas_dict = {p.nome: p.id for p in pessoas}
        self.combo_pessoa['values'] = list(self.pessoas_dict.keys())
    
    def atualizar_lista_etapas(self):
        """Atualiza a árvore de etapas"""
        for item in self.tree_etapas.get_children():
            self.tree_etapas.delete(item)
        
        self.banco_dados.cursor.execute('''
            SELECT e.id, t.nome, e.nome, e.status, p.nome
            FROM etapas e
            JOIN tarefas t ON e.tarefa_id = t.id
            LEFT JOIN pessoas p ON e.pessoa_encarregada_id = p.id
            ORDER BY e.id DESC
        ''')
        
        for row in self.banco_dados.cursor.fetchall():
            responsavel = row[4] or "Não atribuído"
            self.tree_etapas.insert("", "end", values=(row[0], row[1], row[2], row[3], responsavel))
    
    def atualizar_lista_pessoas(self):
        """Atualiza a árvore de pessoas"""
        for item in self.tree_pessoas.get_children():
            self.tree_pessoas.delete(item)
        
        pessoas = self.banco_dados.obter_pessoas()
        for pessoa in pessoas:
            email = pessoa.email or "Não informado"
            self.tree_pessoas.insert("", "end", values=(pessoa.id, pessoa.nome, email))
    
    # ========== Funções de clique ==========
    def adicionar_eixo_clique(self):
        """Manipula clique no botão 'Adicionar Eixo'"""
        nome = self.entry_eixo_nome.get().strip()
        descricao = self.entry_eixo_descricao.get().strip() or None
        
        if not nome:
            messagebox.showwarning("Aviso", "Por favor, preencha o nome do eixo!")
            return
        
        try:
            self.banco_dados.adicionar_eixo(nome, descricao, self.usuario.id)
            messagebox.showinfo("Sucesso", f"✓ Eixo '{nome}' criado com sucesso!")
            self.entry_eixo_nome.delete(0, tk.END)
            self.entry_eixo_descricao.delete(0, tk.END)
            self.atualizar_lista_eixos_tree()
            self.atualizar_combo_eixos()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar eixo: {str(e)}")
    
    def adicionar_tarefa_clique(self):
        """Manipula clique no botão 'Adicionar Tarefa'"""
        eixo_selecionado = self.combo_eixo.get()
        nome = self.entry_tarefa_nome.get().strip()
        prioridade_str = self.combo_prioridade.get()
        
        if not all([eixo_selecionado, nome, prioridade_str]):
            messagebox.showwarning("Aviso", "Por favor, preencha todos os campos!")
            return
        
        try:
            eixo_id = self.eixos_dict[eixo_selecionado]
            # Extrai apenas o número da prioridade (1, 2, 3, 4 ou 5)
            prioridade = int(prioridade_str.split(" - ")[0].replace("⭐", "").strip())
            
            tarefa_id = adicionar_tarefa(
                self.banco_dados,
                eixo_id,
                nome,
                prioridade,
                self.usuario.id
            )
            
            messagebox.showinfo("Sucesso", f"✓ Tarefa '{nome}' criada com sucesso!")
            self.entry_tarefa_nome.delete(0, tk.END)
            self.combo_prioridade.current(-1)
            self.atualizar_lista_tarefas()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar tarefa: {str(e)}")
    
    def adicionar_etapa_clique(self):
        """Manipula clique no botão 'Adicionar Etapa'"""
        tarefa_selecionada = self.combo_tarefa.get()
        nome = self.entry_etapa_nome.get().strip()
        descricao = self.entry_etapa_descricao.get().strip() or None
        pessoa_selecionada = self.combo_pessoa.get()
        
        if not all([tarefa_selecionada, nome]):
            messagebox.showwarning("Aviso", "Por favor, selecione uma tarefa e preencha o nome da etapa!")
            return
        
        try:
            tarefa_id = self.tarefas_dict[tarefa_selecionada]
            pessoa_id = self.pessoas_dict.get(pessoa_selecionada) if pessoa_selecionada else None
            
            etapa_id = adicionar_etapa(
                self.banco_dados,
                tarefa_id,
                nome,
                descricao,
                pessoa_id,
                self.usuario.id
            )
            
            messagebox.showinfo("Sucesso", f"✓ Etapa '{nome}' criada com sucesso!")
            self.entry_etapa_nome.delete(0, tk.END)
            self.entry_etapa_descricao.delete(0, tk.END)
            self.combo_pessoa.current(-1)
            self.atualizar_lista_etapas()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar etapa: {str(e)}")
    
    def adicionar_pessoa_clique(self):
        """Manipula clique no botão 'Adicionar Pessoa'"""
        nome = self.entry_pessoa_nome.get().strip()
        email = self.entry_pessoa_email.get().strip() or None
        
        if not nome:
            messagebox.showwarning("Aviso", "Por favor, preencha o nome da pessoa!")
            return
        
        try:
            self.banco_dados.adicionar_pessoa(nome, email, self.usuario.id)
            messagebox.showinfo("Sucesso", f"✓ Pessoa '{nome}' adicionada com sucesso!")
            self.entry_pessoa_nome.delete(0, tk.END)
            self.entry_pessoa_email.delete(0, tk.END)
            self.atualizar_lista_pessoas()
            self.atualizar_combo_pessoas()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar pessoa: {str(e)}")

            messagebox.showerror("Erro", f"Erro ao adicionar pessoa: {str(e)}")

class VisualizarProjeto:
    """Interface para visualização do projeto"""
    
    def __init__(self, root, usuario):
        self.root = root
        self.usuario = usuario
        self.root.title(f"Visualizar Projeto - OrangeSQL ({usuario.nome})")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Configurar estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        self.banco_dados = BancoDadosSQLite()
        self.setup_interface()
    
    def setup_interface(self):
        """Configura a interface de visualização"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        titulo_label = ttk.Label(
            main_frame, 
            text="📊 Visualização do Projeto", 
            font=("Arial", 16, "bold")
        )
        titulo_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Botão voltar
        btn_voltar = ttk.Button(
            main_frame,
            text="← Voltar ao Menu",
            command=self.voltar_menu
        )
        btn_voltar.grid(row=0, column=2, sticky=tk.E, padx=10)
        
        # Notebook para diferentes visualizações
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Aba de visão geral
        self.frame_geral = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_geral, text="📈 Visão Geral")
        self.setup_aba_geral()
        
        # Aba de eixos e tarefas
        self.frame_eixos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_eixos, text="🏗️ Eixos e Tarefas")
        self.setup_aba_eixos()
        
        # Aba de etapas
        self.frame_etapas = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_etapas, text="📋 Etapas")
        self.setup_aba_etapas()
        
        # Aba de logs
        self.frame_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_logs, text="📝 Logs de Atividades")
        self.setup_aba_logs()
        
        # Configurar expansão
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def setup_aba_geral(self):
        """Configura a aba de visão geral"""
        # Estatísticas
        frame_stats = ttk.LabelFrame(self.frame_geral, text="Estatísticas Gerais", padding="15")
        frame_stats.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        # Obter estatísticas
        stats = self.obter_estatisticas()
        
        ttk.Label(frame_stats, text=f"Total de Eixos: {stats['eixos']}", font=("Arial", 11)).grid(row=0, column=0, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame_stats, text=f"Total de Tarefas: {stats['tarefas']}", font=("Arial", 11)).grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame_stats, text=f"Total de Etapas: {stats['etapas']}", font=("Arial", 11)).grid(row=1, column=0, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame_stats, text=f"Pessoas Envolvidas: {stats['pessoas']}", font=("Arial", 11)).grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Status das tarefas
        frame_status = ttk.LabelFrame(self.frame_geral, text="Status das Tarefas", padding="15")
        frame_status.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Label(frame_status, text=f"Não Iniciadas: {stats['nao_iniciadas']}", font=("Arial", 11), foreground="red").grid(row=0, column=0, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame_status, text=f"Em Andamento: {stats['em_andamento']}", font=("Arial", 11), foreground="orange").grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        ttk.Label(frame_status, text=f"Concluídas: {stats['concluidas']}", font=("Arial", 11), foreground="green").grid(row=1, column=0, sticky=tk.W, pady=5, padx=10)
        
        frame_stats.columnconfigure(0, weight=1)
        frame_stats.columnconfigure(1, weight=1)
        frame_status.columnconfigure(0, weight=1)
        frame_status.columnconfigure(1, weight=1)
    
    def setup_aba_eixos(self):
        """Configura a aba de eixos e tarefas"""
        # Treeview para eixos e tarefas
        colunas = ("Eixo", "Tarefa", "Prioridade", "Status", "Criada em")
        self.tree_projeto = ttk.Treeview(self.frame_eixos, columns=colunas, height=20, show="headings")
        
        self.tree_projeto.column("Eixo", width=150)
        self.tree_projeto.column("Tarefa", width=250)
        self.tree_projeto.column("Prioridade", width=100)
        self.tree_projeto.column("Status", width=120)
        self.tree_projeto.column("Criada em", width=150)
        
        for col in colunas:
            self.tree_projeto.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(self.frame_eixos, orient="vertical", command=self.tree_projeto.yview)
        self.tree_projeto.configure(yscroll=scrollbar.set)
        
        self.tree_projeto.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.frame_eixos.columnconfigure(0, weight=1)
        self.frame_eixos.rowconfigure(0, weight=1)
        
        self.carregar_projeto()
    
    def setup_aba_etapas(self):
        """Configura a aba de etapas"""
        # Treeview para etapas
        colunas = ("Tarefa", "Etapa", "Status", "Responsável", "Criada em")
        self.tree_etapas_vis = ttk.Treeview(self.frame_etapas, columns=colunas, height=20, show="headings")
        
        self.tree_etapas_vis.column("Tarefa", width=200)
        self.tree_etapas_vis.column("Etapa", width=250)
        self.tree_etapas_vis.column("Status", width=120)
        self.tree_etapas_vis.column("Responsável", width=150)
        self.tree_etapas_vis.column("Criada em", width=150)
        
        for col in colunas:
            self.tree_etapas_vis.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(self.frame_etapas, orient="vertical", command=self.tree_etapas_vis.yview)
        self.tree_etapas_vis.configure(yscroll=scrollbar.set)
        
        self.tree_etapas_vis.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.frame_etapas.columnconfigure(0, weight=1)
        self.frame_etapas.rowconfigure(0, weight=1)
        
        self.carregar_etapas()
    
    def setup_aba_logs(self):
        """Configura a aba de logs"""
        # Treeview para logs
        colunas = ("Data/Hora","Usuário", "Ação", "Entidade", "Detalhes")
        self.tree_logs = ttk.Treeview(self.frame_logs, columns=colunas, height=20, show="headings")
        
        self.tree_logs.column("Data/Hora", width=150)
        self.tree_logs.column("Usuário", width=150)
        self.tree_logs.column("Ação", width=100)
        self.tree_logs.column("Entidade", width=120)
        self.tree_logs.column("Detalhes", width=400)
        
        for col in colunas:
            self.tree_logs.heading(col, text=col)
        
        scrollbar = ttk.Scrollbar(self.frame_logs, orient="vertical", command=self.tree_logs.yview)
        self.tree_logs.configure(yscroll=scrollbar.set)
        
        self.tree_logs.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.frame_logs.columnconfigure(0, weight=1)
        self.frame_logs.rowconfigure(0, weight=1)
        
        self.carregar_logs()
    
    def obter_estatisticas(self):
        """Obtém estatísticas gerais do projeto"""
        stats = {
            'eixos': 0,
            'tarefas': 0,
            'etapas': 0,
            'pessoas': 0,
            'nao_iniciadas': 0,
            'em_andamento': 0,
            'concluidas': 0
        }
        
        # Contar eixos
        self.banco_dados.cursor.execute('SELECT COUNT(*) FROM eixos')
        stats['eixos'] = self.banco_dados.cursor.fetchone()[0]
        
        # Contar tarefas e status
        self.banco_dados.cursor.execute('SELECT COUNT(*), status FROM tarefas GROUP BY status')
        for count, status in self.banco_dados.cursor.fetchall():
            stats['tarefas'] += count
            if status == "não iniciada":
                stats['nao_iniciadas'] = count
            elif status == "em andamento":
                stats['em_andamento'] = count
            elif status == "concluído":
                stats['concluidas'] = count
        
        # Contar etapas
        self.banco_dados.cursor.execute('SELECT COUNT(*) FROM etapas')
        stats['etapas'] = self.banco_dados.cursor.fetchone()[0]
        
        # Contar pessoas
        self.banco_dados.cursor.execute('SELECT COUNT(*) FROM pessoas')
        stats['pessoas'] = self.banco_dados.cursor.fetchone()[0]
        
        return stats
    
    def carregar_projeto(self):
        """Carrega os dados do projeto na treeview"""
        for item in self.tree_projeto.get_children():
            self.tree_projeto.delete(item)
        
        self.banco_dados.cursor.execute('''
            SELECT e.nome, t.nome, t.prioridade, t.status, t.data_criacao
            FROM tarefas t
            JOIN eixos e ON t.eixo_id = e.id
            ORDER BY e.nome, t.prioridade DESC, t.data_criacao DESC
        ''')
        
        for row in self.banco_dados.cursor.fetchall():
            prioridade = f"⭐ {row[2]}" if row[2] else "N/A"
            self.tree_projeto.insert("", "end", values=(row[0], row[1], prioridade, row[3], row[4]))
    
    def carregar_etapas(self):
        """Carrega as etapas na treeview"""
        for item in self.tree_etapas_vis.get_children():
            self.tree_etapas_vis.delete(item)
        
        self.banco_dados.cursor.execute('''
            SELECT t.nome, e.nome, e.status, p.nome, e.data_criacao
            FROM etapas e
            JOIN tarefas t ON e.tarefa_id = t.id
            LEFT JOIN pessoas p ON e.pessoa_encarregada_id = p.id
            ORDER BY t.nome, e.data_criacao DESC
        ''')
        
        for row in self.banco_dados.cursor.fetchall():
            responsavel = row[3] or "Não atribuído"
            self.tree_etapas_vis.insert("", "end", values=(row[0], row[1], row[2], responsavel, row[4]))
    
    def carregar_logs(self):
        """Carrega os logs na treeview"""
        for item in self.tree_logs.get_children():
            self.tree_logs.delete(item)
        
        logs = self.banco_dados.obter_logs_usuario(self.usuario.id)
        
        for log in logs:
            self.tree_logs.insert("", "end", values=(
                log.data_hora,
                log.acao,
                f"{log.entidade} #{log.entidade_id}",
                log.detalhes
            ))
    
    def voltar_menu(self):
        """Volta ao menu principal"""
        self.root.destroy()
        root_menu = tk.Tk()
        app = MenuPrincipal(root_menu, self.usuario)
        root_menu.mainloop()

# ==================== FUNÇÃO PRINCIPAL ====================
def main():
    # Criar usuário padrão se não existir
    banco_temp = BancoDadosSQLite()
    banco_temp.criar_usuario_padrao()
    
    # Iniciar com tela de login
    root = tk.Tk()
    app = TelaLogin(root)
    root.mainloop()

if __name__ == "__main__":
    main()
