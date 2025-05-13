# Validador OPIN

Sistema de validação para o Open Insurance Brasil (OPIN), com processamento de schemas YAML e persistência em banco de dados.

## Sobre o Projeto

O Validador OPIN é uma aplicação completa para validação e gerência das especificações YAML do Open Insurance Brasil. O sistema realiza o download automático das especificações, verifica sua conformidade e persiste as regras de validação em banco de dados para uso em validações de APIs.

### Funcionalidades Principais

- **Download automático de especificações YAML**: Obtenção das últimas versões das APIs OPIN
- **Validação de estrutura**: Verificação da conformidade dos schemas
- **Persistência de regras**: Armazenamento estruturado das regras em banco de dados
- **Consistência de schemas**: Identificação e correlação de schemas relacionados
- **Acompanhamento de saúde**: Monitoramento do estado das APIs OPIN
- **Agendamento de verificações**: Execução autônoma e periódica de verificações

## Estrutura do Projeto

```
validador-opin/
├── App/
│   ├── backend/     # Backend em Python/FastAPI
│   └── frontend/    # Frontend em React/Vite
└── documentos/      # Documentação do projeto
```

## Backend

### Tecnologias Utilizadas

- **Python 3.11+**: Linguagem principal
- **FastAPI**: Framework web de alta performance
- **SQLAlchemy**: ORM para comunicação com banco de dados
- **PyYAML**: Processamento de arquivos YAML
- **SQL Server**: Banco de dados relacional

### Configuração do Ambiente

#### Pré-requisitos

- Python 3.8 ou superior
- SQL Server 2022
- Driver ODBC para SQL Server

#### Instalação

1. Clone o repositório

2. Crie e ative um ambiente virtual Python:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente (ou crie um arquivo .env na raiz do diretório backend):

```
SECRET_KEY=sua-chave-secreta
AES_KEY=sua-chave-aes-de-32-caracteres
DB_HOST=localhost
DB_PORT=1435
DB_NAME=db_validador
DB_SCHEMA=validador_opin
DB_USER=sa
DB_PASSWORD=sua-senha
```

### Executando a Aplicação

```bash
cd App/backend
uvicorn app.main:app --reload
```

A API estará disponível em http://localhost:8000

A documentação da API estará disponível em:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Processos Principais

#### Verificação OPIN

O processo de verificação OPIN pode ser executado manualmente ou agendado:

```bash
# Verificação completa
python run_opin_verification.py

# Verificação diária agendada
python schedule_daily_verification.py

# Apenas para APIs críticas
python schedule_daily_verification.py --critical-only
```

## Frontend

### Tecnologias Utilizadas

- **React 19**: Biblioteca para interfaces de usuário
- **Vite**: Build tool e servidor de desenvolvimento
- **Tailwind CSS**: Framework CSS para estilização
- **React Query**: Gerenciamento de estado e cache
- **React Router**: Navegação

### Execução

```bash
cd App/frontend
npm install
npm run dev
```

O frontend estará disponível em http://localhost:5173

## Processamento de Arquivos Relacionados a Seguros

O sistema identifica e processa especialmente os arquivos relacionados a seguros, incluindo:

- Todos os arquivos que começam com "insurance-"
- Arquivos especiais como `person.yaml` e `resources_v2.yaml`

Esses arquivos recebem tratamento específico para garantir a consistência dos schemas, incluindo a adição da propriedade `policyId` e o tratamento adequado de referências entre schemas.

## Licença

Este projeto é disponibilizado sob a licença MIT.