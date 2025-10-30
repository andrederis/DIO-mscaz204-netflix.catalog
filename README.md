# Gerenciador de Catálogos da Netflix — Azure Functions + SQL

Este projeto implementa um serviço simples de gerenciamento de catálogos da Netflix utilizando **Azure Functions (Python)** e **Banco de Dados SQL**.  
Ele pode ser executado localmente e, opcionalmente, publicado na Azure com um banco Azure SQL Database.

---

## Estrutura do Projeto

/project-root
│
├── function_app.py          # Código principal com as rotas da API
├── host.json                # Configuração do runtime da Function
├── local.settings.json      # Variáveis locais (connection string, etc.)
├── requirements.txt         # Dependências do projeto
└── README.md                # Documentação

---

## Banco de Dados

O projeto pode ser configurado com **SQL Server local** (para desenvolvimento) ou **Azure SQL Database** (para publicação na nuvem).

### Opção 1 - Banco Local (SQL Server Express)

1. Instale o **SQL Server Express** e o **ODBC Driver 17 for SQL Server**.
2. Crie um banco chamado `CatalogoNetflix`.
3. Execute o script abaixo para criar a tabela de catálogos:

CREATE TABLE dbo.titulos (
  id INT IDENTITY(1,1) PRIMARY KEY,
  titulo NVARCHAR(200) NOT NULL,
  ano INT NULL,
  genero NVARCHAR(50) NULL,
  rating DECIMAL(3,1) NULL,
  is_active BIT NOT NULL DEFAULT 1,
  created_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

4. No arquivo `local.settings.json`, configure a variável de ambiente `SQL_CONNSTR` conforme o exemplo:

DRIVER={ODBC Driver 17 for SQL Server};
SERVER=localhost;
DATABASE=CatalogoNetflix;
Trusted_Connection=yes;

### Opção 2 - Banco de Dados na Azure (Azure SQL Database)

1. Crie um **Azure SQL Database** no portal Azure.
2. Libere seu IP no firewall do banco.
3. Crie a mesma tabela utilizando o script SQL mostrado acima.
4. Configure a string de conexão no formato:

DRIVER={ODBC Driver 17 for SQL Server};
SERVER=<seu-servidor>.database.windows.net;
DATABASE=CatalogoNetflix;
UID=<usuario>;
PWD=<senha>;

5. Em ambiente Azure, defina a variável `SQL_CONNSTR` em  
   **Function App → Configuration → Application Settings**.

---

## Execução Local

Pré-requisitos:
- Python 3.9 ou superior (recomendado 3.11)
- Azure Functions Core Tools v4
- VS Code com extensão Azure Functions

Passos:

# Criar e ativar ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor local
func start

Acesse no navegador para testar o endpoint básico:

http://localhost:7071/api/health

Resposta esperada:
{"status": "ok", "service": "catalogo-netflix"}

---

## Endpoints Planejados

| Método | Rota                         | Descrição                     |
|--------|------------------------------|--------------------------------|
| GET    | /api/health                  | Teste de status da aplicação   |
| POST   | /api/catalog/titles          | Criar novo título              |
| GET    | /api/catalog/titles          | Listar títulos                 |
| GET    | /api/catalog/titles/{id}     | Consultar título por ID        |
| PUT    | /api/catalog/titles/{id}     | Atualizar informações          |
| DELETE | /api/catalog/titles/{id}     | Excluir (soft delete)          |

---

## Observações

- O arquivo `local.settings.json` é usado apenas para desenvolvimento local e **não deve conter senhas públicas**.
- Em produção, as credenciais são configuradas como variáveis seguras na Azure.
- O plano **Consumption (Serverless)** da Azure Functions é gratuito dentro da cota de 1 milhão de execuções/mês.

---

## Publicação na Azure

1. No VS Code, instale as extensões:
   - Azure Functions
   - Azure Account
2. Faça login: `Ctrl+Shift+P → Azure: Sign In`
3. Crie e configure o Function App:
   - `Ctrl+Shift+P → Azure Functions: Deploy to Function App`
   - Runtime: Python 3.11, Linux
   - Plano: Consumption (Serverless)
4. Configure `SQL_CONNSTR` no portal em:
   Function App → Configuration → Application Settings
5. O endpoint público ficará disponível em:
   https://andrederis.azurewebsites.net/api/catalog/titles