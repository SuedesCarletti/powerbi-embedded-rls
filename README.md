# Power BI Embedded - Sistema de Dashboards Corporativos

Sistema completo de visualização de dashboards Power BI com autenticação segura, controle de acesso por perfil e região, e interface moderna.

## Arquitetura do Sistema

```
Power BI Embedded System
├── Autenticação Segura (auth.py)
├── Múltiplos Dashboards (config.py)
├── Interface Moderna (templates/)
├── Integração Power BI (powerbi_service.py)
└── Deploy Automático (Railway)
```

## Início Rápido

### 1. Configuração Inicial

```bash
# Clone o projeto
git clone <seu-repositorio>
cd powerbi-embedded

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais
```

### 2. Configuração das Variáveis de Ambiente

Crie as seguintes variáveis no Railway ou arquivo `.env`:

```env
# ===== CREDENCIAIS POWER BI =====
CLIENT_ID=seu_client_id_do_azure
CLIENT_SECRET=seu_client_secret
TENANT_ID=seu_tenant_id
WORKSPACE_ID=workspace_id_principal

# ===== SEGURANÇA =====
SECRET_KEY=sua_chave_secreta_super_forte

# ===== USUÁRIOS (JSON) =====
USERS_CONFIG={"admin":{"password":"REDACTED_SECRET","roles":["admin"],"region":"SP","name":"Administrador","reports":["all"]}}

# ===== RELATÓRIOS INDIVIDUAIS =====
REPORT_ID_EXECUTIVO=id_do_relatorio_executivo
REPORT_ID_VENDAS=id_do_relatorio_vendas
REPORT_ID_FINANCEIRO=id_do_relatorio_financeiro

# ===== METADADOS DOS RELATÓRIOS =====
METADATA_EXECUTIVO={"name":"Dashboard Executivo","description":"KPIs principais","category":"executivo","required_roles":["admin","director"],"background_color":"#002951"}
```

## Gerenciamento de Usuários

### Como Adicionar Novos Usuários

#### Método 1: Via Variável de Ambiente (Recomendado)

1. **Gere o hash da senha:**
```python
import hashlib
senha = "REDACTED_SECRET"
hash_senha = hashlib.sha256(senha.encode()).hexdigest()
print(hash_senha)
```

2. **Atualize USERS_CONFIG no Railway:**
```json
{
  "admin": {
    "password": "REDACTED_SECRET",
    "roles": ["admin"],
    "region": "SP",
    "name": "Administrador",
    "reports": ["all"]
  },
  "novo.usuario": {
    "password": "REDACTED_SECRET",
    "roles": ["viewer"],
    "region": "RJ",
    "name": "Novo Usuário",
    "reports": ["executivo", "vendas"]
  }
}
```

#### Método 2: Via Script Automatizado

```bash
# Execute o script de configuração segura
python setup_railway_variables.py
```

### Perfis de Usuário Disponíveis

| Role | Descrição | Permissões |
|------|-----------|------------|
| `admin` | Administrador | Acesso total, controles avançados |
| `director` | Diretor | Acesso a dashboards gerenciais |
| `viewer` | Visualizador | Acesso básico a relatórios |
| `sales` | Vendas | Acesso a relatórios de vendas |
| `finance` | Financeiro | Acesso a relatórios financeiros |
| `logistics` | Logística | Acesso a relatórios de logística |
| `purchasing` | Compras | Acesso a relatórios de compras |
| `salesman` | Vendedor | Acesso limitado a vendas |

### Regiões Disponíveis

- `SP` - São Paulo
- `RJ` - Rio de Janeiro  
- `PR` - Paraná
- `MG` - Minas Gerais
- `RS` - Rio Grande do Sul

### Como Alterar Dados de Usuário

1. **Alterar Senha:**
```python
# Gerar novo hash
novo_hash = hashlib.sha256("nova_senha".encode()).hexdigest()
# Atualizar no USERS_CONFIG
```

2. **Alterar Permissões:**
```json
{
  "usuario.existente": {
    "password": "REDACTED_SECRET",
    "roles": ["admin", "finance"],  // ← Adicionar/remover roles
    "region": "SP",
    "name": "Nome Atualizado",  // ← Alterar nome
    "reports": ["executivo", "financeiro"]  // ← Alterar relatórios
  }
}
```

3. **Aplicar Mudanças:**
- Atualize `USERS_CONFIG` no Railway
- Faça redeploy da aplicação

## Gerenciamento de Dashboards

### Como Adicionar Novo Dashboard

#### Passo 1: Obter IDs do Power BI
```bash
# Execute o script de descoberta
python test_integration.py
```

#### Passo 2: Configurar Variáveis
```env
# Adicione no Railway:
REPORT_ID_NOVODASH=id_do_novo_relatorio
DATASET_ID_NOVODASH=id_do_dataset (opcional)
WORKSPACE_ID_NOVODASH=id_workspace (opcional, usa principal)

# Metadados do dashboard:
METADATA_NOVODASH={"name":"Novo Dashboard","description":"Descrição do dashboard","category":"categoria","required_roles":["admin"],"background_color":"#002951","workspace_name":"Nome do Workspace"}
```

#### Passo 3: Categorias Disponíveis
- `executivo` - Dashboards de alta gestão
- `gerencial` - Relatórios gerenciais
- `vendas` - Métricas de vendas
- `financeiro` - Dados financeiros
- `marketing` - Campanhas e leads
- `rh` - Recursos humanos
- `operacional` - Operações diárias
- `logistica` - Logística e transporte
- `outros` - Categoria geral

### Como Alterar Nome de Dashboard

1. **Método Simples (Metadata):**
```json
{
  "name": "Novo Nome do Dashboard",
  "description": "Nova descrição",
  "category": "categoria",
  "required_roles": ["admin", "viewer"],
  "background_color": "#002951"
}
```

2. **Atualizar variável:**
```env
METADATA_NOMEDASH={"name":"Nome Atualizado","description":"Descrição nova",...}
```

### Personalização de Cores

#### Cores Corporativas Disponíveis:
```css
--corporate-primary: #002951      /* Azul principal */
--corporate-light: #0d4a73        /* Azul claro */
--corporate-dark: #001a2e         /* Azul escuro */
--background-light: #f8f9fa       /* Fundo claro */
--background-blue: #e3f2fd        /* Azul claro */
```

#### Configurar Cor do Dashboard:
```json
{
  "background_color": "#002951",    // Cor de fundo
  "text_color": "#ffffff"          // Cor do texto (opcional)
}
```

## Configuração Avançada

### Row-Level Security (RLS)

Para ativar segurança por linha:

```env
ENABLE_RLS=true
DATASET_ID_DASHBOARD=id_do_dataset_com_rls
```

### Controle de Acesso Detalhado

```json
{
  "usuario.vendas": {
    "password": "hash",
    "roles": ["sales", "viewer"],
    "region": "SP",
    "name": "Vendedor",
    "reports": ["vendas", "clientes"]  // ← Apenas dashboards específicos
  }
}
```

### Configurações de Interface

```json
{
  "required_roles": ["admin"],           // Quem pode ver
  "required_regions": ["SP", "RJ"],     // Regiões permitidas
  "background_color": "#002951",        // Cor de fundo
  "workspace_name": "Vendas 2024"       // Nome do workspace
}
```

## Deploy e Produção

### Railway Deploy

1. **Conectar Repositório:**
   - Acesse [Railway](https://railway.app)
   - Conecte seu repositório GitHub

2. **Configurar Variáveis:**
   - Vá em "Variables"
   - Adicione todas as variáveis de ambiente

3. **Deploy Automático:**
   - Push para main = deploy automático
   - Logs disponíveis em "Deployments"

### Variáveis Essenciais para Produção:
```env
# Obrigatórias
CLIENT_ID=...
CLIENT_SECRET=...
TENANT_ID=...
WORKSPACE_ID=...
SECRET_KEY=...
USERS_CONFIG=...

# Dashboards
REPORT_ID_EXECUTIVO=...
METADATA_EXECUTIVO=...

# Configurações
FLASK_ENV=production
LOG_LEVEL=INFO
```

## Scripts Utilitários

### Diagnóstico do Sistema
```bash
# Verificar configuração completa
python diagnose_powerbi.py

# Testar conexão específica
python debug_railway.py

# Descobrir novos relatórios
python setup_reports.py
```

### Testes Locais
```bash
# Servidor local
python app.py

# Acesse: http://localhost:5000
# Login: admin / admin123
```

## Checklist de Configuração

### Configuração Inicial
- [ ] Credenciais Azure configuradas
- [ ] WORKSPACE_ID definido
- [ ] SECRET_KEY gerada
- [ ] USERS_CONFIG criada

### Dashboards
- [ ] REPORT_ID_* definidos
- [ ] METADATA_* configuradas
- [ ] Cores corporativas aplicadas
- [ ] Permissões definidas

### Usuários
- [ ] Admin principal criado
- [ ] Senhas em hash SHA256
- [ ] Roles apropriadas
- [ ] Regiões definidas

### Produção
- [ ] Deploy no Railway
- [ ] Variáveis de ambiente
- [ ] Logs funcionando
- [ ] Acesso testado

## Troubleshooting

### Problemas Comuns

#### 1. **Erro "Relatório não encontrado"**
```bash
# Verificar configuração
python diagnose_powerbi.py

# Conferir se REPORT_ID_* está correto
echo $REPORT_ID_EXECUTIVO
```

#### 2. **Usuário não consegue logar**
```python
# Verificar hash da senha
import hashlib
senha = "REDACTED_SECRET"
hash_calculado = hashlib.sha256(senha.encode()).hexdigest()
print(f"Hash: {hash_calculado}")
# Compare com o hash no USERS_CONFIG
```

#### 3. **Dashboard não carrega**
```bash
# Testar token do Power BI
python test_integration.py

# Verificar logs no Railway
# Dashboard → Deployments → View Logs
```

#### 4. **Permissão negada**
- Verificar se usuário tem role necessária
- Confirmar região do usuário
- Checar lista de relatórios permitidos

### Logs e Debug

#### Logs Importantes:
```bash
# No Railway: Deployments → View Logs
# Procurar por:
PowerBIService inicializado
Sistema de relatórios: flexible
Usuário logado: username
Embed do relatório 'nome' acessado
```

#### Debug Local:
```python
# Verificar configuração
from config import Config
Config.test_config()

# Verificar usuários
from auth import validate_user_config
issues = validate_user_config()
print(issues)
```

## Referências

- [Power BI Embedded API](https://docs.microsoft.com/en-us/power-bi/developer/embedded/)
- [Azure App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Railway Documentation](https://docs.railway.app/)

## Exemplos Práticos

### Exemplo 1: Usuário de Vendas
```json
{
  "joao.vendas": {
    "password": "REDACTED_SECRET",
    "roles": ["sales", "viewer"],
    "region": "SP",
    "name": "João Silva - Vendas",
    "reports": ["vendas", "clientes", "metas"]
  }
}
```

### Exemplo 2: Dashboard Financeiro
```env
REPORT_ID_FINANCEIRO=00000000-0000-0000-0000-000000000028
METADATA_FINANCEIRO={"name":"Dashboard Financeiro","description":"Relatórios de faturamento, custos e margem","category":"financeiro","required_roles":["admin","finance","director"],"background_color":"#f8f9fa","workspace_name":"Financeiro 2024"}
```

### Exemplo 3: USERS_CONFIG Completa
```json
{
  "admin": {
    "password": "REDACTED_SECRET",
    "roles": ["admin"],
    "region": "SP",
    "name": "Administrador do Sistema",
    "reports": ["all"]
  },
  "diretor.geral": {
    "password": "REDACTED_SECRET",
    "roles": ["director", "admin"],
    "region": "SP", 
    "name": "Diretor Geral",
    "reports": ["executivo", "gerencial", "financeiro"]
  },
  "vendas.sp": {
    "password": "REDACTED_SECRET",
    "roles": ["sales", "viewer"],
    "region": "SP",
    "name": "Equipe Vendas SP",
    "reports": ["vendas", "clientes"]
  }
}
```

---

## Sistema Pronto para Uso!

Este README fornece todas as informações necessárias para:
- Gerenciar usuários completo
- Adicionar/editar dashboards  
- Configurar permissões
- Deploy em produção
- Troubleshooting

Para suporte adicional, consulte os logs da aplicação ou execute os scripts de diagnóstico fornecidos.
