from flask import session, request, redirect, url_for, flash
from functools import wraps
import hashlib
import os
import json
import logging
from werkzeug.security import check_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ========== SISTEMA DE USUÁRIOS SEGURO ==========
# NUNCA mais senhas hardcoded! Apenas exemplos para demonstração

def load_users_from_env():
    """
    Carrega os usuários da variável de ambiente USERS_CONFIG (ou do arquivo .env).

    Formato (JSON); "password" é um hash gerado por setup_railway_variables.py
    (werkzeug), nunca a senha em texto:
    {
        "admin": {
            "password": "<hash>",
            "roles": ["admin"],
            "region": "SP",
            "name": "Administrador",
            "reports": ["all"]
        }
    }
    Sem USERS_CONFIG válido, ninguém consegue entrar (não há usuários padrão).
    """
    users_json = os.getenv('USERS_CONFIG')
    if not users_json:
        logger.error("USERS_CONFIG não definido: nenhum usuário disponível. "
                     "Rode setup_railway_variables.py e coloque o resultado no .env")
        return {}
    try:
        env_users = json.loads(users_json)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar USERS_CONFIG: {e}")
        return {}

    for username, user_data in env_users.items():
        missing = [f for f in ('password', 'roles', 'region', 'name') if f not in user_data]
        if missing:
            logger.warning(f"Usuário {username} está faltando campos: {missing}")
    logger.info(f"Carregados {len(env_users)} usuários do ambiente")
    return env_users

def login_required(f):
    """Decorator para páginas que requerem login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para páginas que requerem privilégios de admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
            
        user_roles = session['user'].get('roles', [])
        if 'admin' not in user_roles:
            flash('❌ Acesso negado. Privilégios de administrador necessários.')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def authenticate_user(username, password):
    """
    Autentica o usuário comparando a senha com o hash guardado em USERS_CONFIG.

    Returns:
        dict|None: dados do usuário (sem a senha) se autenticado, None se falhou
    """
    users = load_users_from_env()
    logger.info(f"Tentativa de login: {username}")

    # Rate limiting básico
    session_key = f"login_attempts_{username}"
    attempts = session.get(session_key, 0)
    if attempts >= 5:
        logger.warning(f"Muitas tentativas para: {username}")
        return None

    user_data = users.get(username)
    if user_data and check_password_hash(user_data["password"], password):
        session.pop(session_key, None)
        user_result = user_data.copy()
        user_result["username"] = username
        user_result.pop('password', None)
        logger.info(f"Login bem-sucedido para: {username}")
        return user_result

    session[session_key] = attempts + 1
    logger.warning(f"Falha de login para: {username} (tentativa {attempts + 1})")
    return None

def get_user_identity():
    """
    Retorna identidade do usuário para Row-Level Security (RLS)
    
    Returns:
        dict|None: Identidade para RLS ou None se não logado
    """
    if 'user' not in session:
        return None
        
    user_data = session['user']
    
    # Usar região como filtro RLS principal
    identity = {
        "username": user_data["region"],  # Filtrar por região
        "roles": ["RegionalFilter"],      # Role criada no Power BI
        "datasets": []                    # Pode especificar datasets específicos
    }
    
    # Adicionar informações extras para RLS avançado
    user_roles = user_data.get('roles', [])
    if 'admin' in user_roles:
        identity["roles"].append("AdminRole")
    if 'finance' in user_roles:
        identity["roles"].append("FinanceRole")
    if 'sales' in user_roles:
        identity["roles"].append("SalesRole")
    if 'logistics' in user_roles:
        identity["roles"].append("LogisticsRole")
    if 'purchasing' in user_roles:
        identity["roles"].append("PurchasingRole")
    if 'director' in user_roles:
        identity["roles"].append("DirectorRole")
    if 'salesman' in user_roles:
        identity["roles"].append("SalesmanRole")
    if 'manager' in user_roles:
        identity["roles"].append("ManagerRole")
    if 'analyst' in user_roles:
        identity["roles"].append("AnalystRole")
    if 'assistant' in user_roles:
        identity["roles"].append("AssistantRole")
    if 'ecommerce' in user_roles:
        identity["roles"].append("EcommerceRole")
    
    return identity

def user_can_access_report(report_name_or_id):
    """
    Verifica se o usuário atual pode acessar um relatório específico.
    
    ATUALIZADO: Suporta tanto nomes de relatórios (novo sistema) quanto IDs (compatibilidade).
    
    Args:
        report_name_or_id (str): Nome do relatório (ex: 'executivo') ou ID (GUID)
        
    Returns:
        bool: True se pode acessar, False caso contrário
    """
    if 'user' not in session:
        return False
    
    user = session['user']
    user_reports = user.get('reports', [])
    user_roles = user.get('roles', [])
    user_region = user.get('region')
    
    logger.debug(f"Verificando acesso do usuário {user['username']} ao relatório {report_name_or_id}")
    logger.debug(f"   Roles: {user_roles}")
    logger.debug(f"   Região: {user_region}")
    logger.debug(f"   Relatórios permitidos: {user_reports}")
    
    # Admin sempre pode acessar tudo
    if 'admin' in user_roles:
        logger.debug(f"Acesso liberado: usuário é admin")
        return True
    
    # Verificar se tem acesso a todos os relatórios
    if 'all' in user_reports:
        logger.debug(f"Acesso liberado: usuário tem acesso total")
        return True
    
    # Verificar se tem acesso ao relatório específico pelo nome
    if report_name_or_id in user_reports:
        logger.debug(f"Acesso liberado: relatório está na lista do usuário")
        return True
    
    # Verificação adicional: carregar configuração do relatório para verificar roles/região
    try:
        from config import Config
        
        # Tentar buscar por nome primeiro (novo sistema)
        report_config = Config.get_report_by_name(report_name_or_id)
        
        # Se não encontrou por nome, tentar por ID (compatibilidade)
        if not report_config:
            report_config = Config.get_report_by_id(report_name_or_id)
        
        if report_config:
            # Verificar roles necessárias
            required_roles = report_config.get('required_roles', [])
            if required_roles and not any(role in user_roles for role in required_roles):
                logger.debug(f"Acesso negado: usuário não tem roles necessárias {required_roles}")
                return False
            
            # Verificar região
            required_regions = report_config.get('required_regions')
            if required_regions and user_region not in required_regions:
                logger.debug(f"Acesso negado: usuário não está nas regiões necessárias {required_regions}")
                return False
            
            logger.debug(f"Acesso liberado: usuário atende aos critérios do relatório")
            return True
        else:
            logger.warning(f"Relatório '{report_name_or_id}' não encontrado na configuração")
            
    except Exception as e:
        logger.error(f"Erro ao verificar configuração do relatório: {e}")
    
    logger.debug(f"Acesso negado: usuário não tem permissão")
    return False

def get_user_reports():
    """
    Retorna lista de relatórios que o usuário atual pode acessar
    
    Returns:
        str|list: 'all' para acesso total ou lista de report_ids
    """
    if 'user' not in session:
        return []
    
    user = session['user']
    user_roles = user.get('roles', [])
    
    # Admin pode ver tudo
    if 'admin' in user_roles:
        return 'all'
    
    return user.get('reports', [])

def is_user_admin():
    """
    Verifica se o usuário atual é admin
    
    Returns:
        bool: True se é admin, False caso contrário
    """
    if 'user' not in session:
        return False
        
    user_roles = session['user'].get('roles', [])
    return 'admin' in user_roles

def get_current_user():
    """
    Retorna dados do usuário atual da sessão
    
    Returns:
        dict|None: Dados do usuário ou None se não logado
    """
    return session.get('user')

def logout_user():
    """Remove usuário da sessão (logout)"""
    user = session.get('user', {}).get('username', 'desconhecido')
    session.clear()
    logger.info(f"Usuário deslogado: {user}")

def get_accessible_reports_for_user(user_data):
    """
    Retorna relatórios acessíveis para um usuário específico considerando o novo sistema.
    
    Args:
        user_data (dict): Dados do usuário
        
    Returns:
        dict: Relatórios que o usuário pode acessar
    """
    try:
        from config import Config
        
        user_roles = user_data.get('roles', [])
        user_region = user_data.get('region')
        user_reports = user_data.get('reports', [])
        
        # Admin sempre pode ver tudo
        if 'admin' in user_roles:
            return Config.get_reports_config()
        
        # Se tem acesso a todos os relatórios, usar filtro por roles/região
        if 'all' in user_reports:
            return Config.get_reports_for_user(user_roles, user_region)
        
        # Filtrar relatórios específicos do usuário
        all_reports = Config.get_reports_config()
        accessible_reports = {}
        
        for report_name, config in all_reports.items():
            # Verificar se está na lista do usuário
            if report_name in user_reports:
                # Verificar roles necessárias
                required_roles = config.get('required_roles', [])
                if required_roles and not any(role in user_roles for role in required_roles):
                    continue
                
                # Verificar região
                required_regions = config.get('required_regions')
                if required_regions and user_region not in required_regions:
                    continue
                
                accessible_reports[report_name] = config
        
        return accessible_reports
        
    except Exception as e:
        logger.error(f"Erro ao obter relatórios acessíveis: {e}")
        return {}

def user_has_role(role):
    """
    Verifica se o usuário atual tem uma role específica
    
    Args:
        role (str): Role a verificar
        
    Returns:
        bool: True se tem a role, False caso contrário
    """
    if 'user' not in session:
        return False
    
    user_roles = session['user'].get('roles', [])
    return role in user_roles

def user_in_region(region):
    """
    Verifica se o usuário atual está em uma região específica
    
    Args:
        region (str): Região a verificar
        
    Returns:
        bool: True se está na região, False caso contrário
    """
    if 'user' not in session:
        return False
    
    user_region = session['user'].get('region')
    return user_region == region

# ========== UTILITÁRIOS DE SEGURANÇA ==========

def generate_password_hash(password):
    """
    Utilitário para gerar hash de senha
    
    Args:
        password (str): Senha em texto plano
        
    Returns:
        str: Hash SHA256 da senha
    """
    return hashlib.sha256(password.encode()).hexdigest()

def create_user_config(users_dict):
    """
    Cria configuração JSON de usuários para variáveis de ambiente
    
    Args:
        users_dict (dict): Dicionário com usuários e senhas em texto plano
        
    Returns:
        str: JSON string para USERS_CONFIG
        
    Example:
        users = {
            "admin": {"password": "REDACTED_SECRET", "roles": ["admin"], "region": "SP", "name": "Admin"}
        }
        json_config = create_user_config(users)
    """
    secure_users = {}
    
    for username, user_data in users_dict.items():
        secure_user = user_data.copy()
        
        # Hash da senha se estiver em texto plano
        if 'password' in secure_user:
            if len(secure_user['password']) != 64:  # Não é hash SHA256
                secure_user['password'] = generate_password_hash(secure_user['password'])
                
        secure_users[username] = secure_user
    
    return json.dumps(secure_users, indent=2)

def validate_user_config():
    """
    Valida se a configuração de usuários está segura
    
    Returns:
        list: Lista de problemas encontrados
    """
    issues = []
    users = load_users_from_env()
    
    # Verificar se há usuários
    if not users:
        issues.append("Nenhum usuário configurado")
        return issues
    
    # Verificar cada usuário
    for username, user_data in users.items():
        # Campos obrigatórios
        required_fields = ['password', 'roles', 'region', 'name']
        for field in required_fields:
            if field not in user_data:
                issues.append(f"Usuário {username}: campo '{field}' ausente")
        
        # Verificar se senha é hash
        password = user_data.get('password', '')
        if len(password) != 64:
            issues.append(f"Usuário {username}: senha não está em formato hash")
        
        # Verificar roles
        roles = user_data.get('roles', [])
        if not isinstance(roles, list) or not roles:
            issues.append(f"Usuário {username}: roles deve ser lista não vazia")
        
        # Verificar reports
        reports = user_data.get('reports', [])
        if not isinstance(reports, list) or not reports:
            issues.append(f"Usuário {username}: reports deve ser lista não vazia")
    
    # Verificar se tem pelo menos um admin
    if not any('admin' in user.get('roles', []) for user in users.values()):
        issues.append("Nenhum usuário com role 'admin' encontrado")
    
    # Verificar senhas padrão em produção
    is_production = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('FLASK_ENV') == 'production'
    if is_production:
        default_hashes = [
            hashlib.sha256("admin123".encode()).hexdigest(),
            hashlib.sha256("viewer123".encode()).hexdigest(),
            hashlib.sha256("sp123".encode()).hexdigest(),
            hashlib.sha256("rj123".encode()).hexdigest(),
            hashlib.sha256("vendas123".encode()).hexdigest(),
            hashlib.sha256("financeiro123".encode()).hexdigest(),
        ]
        
        for username, user_data in users.items():
            if user_data.get('password') in default_hashes:
                issues.append(f"PRODUÇÃO: Usuário {username} usando senha padrão INSEGURA!")
    
    return issues

def get_user_statistics():
    """
    Retorna estatísticas dos usuários configurados
    
    Returns:
        dict: Estatísticas dos usuários
    """
    users = load_users_from_env()
    
    stats = {
        'total_users': len(users),
        'by_role': {},
        'by_region': {},
        'with_all_reports': 0,
        'with_specific_reports': 0
    }
    
    for username, user_data in users.items():
        # Contar por role
        roles = user_data.get('roles', [])
        for role in roles:
            stats['by_role'][role] = stats['by_role'].get(role, 0) + 1
        
        # Contar por região
        region = user_data.get('region', 'N/A')
        stats['by_region'][region] = stats['by_region'].get(region, 0) + 1
        
        # Contar tipo de acesso a relatórios
        reports = user_data.get('reports', [])
        if 'all' in reports:
            stats['with_all_reports'] += 1
        else:
            stats['with_specific_reports'] += 1
    
    return stats

# ========== EXEMPLO DE USO ==========

if __name__ == "__main__":
    print("TESTE DO SISTEMA DE AUTENTICAÇÃO SEGURO")
    print("=" * 60)
    
    # Validar configuração atual
    issues = validate_user_config()
    if issues:
        print("Problemas de segurança encontrados:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("Configuração de usuários OK")
    
    # Mostrar estatísticas de usuários
    stats = get_user_statistics()
    print(f"\nEstatísticas de usuários:")
    print(f"   Total: {stats['total_users']}")
    print(f"   Por role: {dict(stats['by_role'])}")
    print(f"   Por região: {dict(stats['by_region'])}")
    print(f"   Com acesso total: {stats['with_all_reports']}")
    print(f"   Com acesso específico: {stats['with_specific_reports']}")
    
    # Mostrar usuários carregados (sem senhas)
    users = load_users_from_env()
    print(f"\nUsuários configurados:")
    
    for username, user_data in users.items():
        print(f"\n{username}:")
        print(f"   Nome: {user_data.get('name')}")
        print(f"   Roles: {user_data.get('roles', [])}")
        print(f"   Região: {user_data.get('region')}")
        print(f"   Relatórios: {user_data.get('reports', [])}")
        print(f"   Senha: {'*' * len(user_data.get('password', ''))}")
    
    print(f"\nLEMBRETE DE SEGURANÇA:")
    print("• NUNCA commite senhas em código")
    print("• Use sempre USERS_CONFIG nas variáveis de ambiente") 
    print("• Senhas devem ser fortes e únicas")
    print("• Em produção, mude todas as senhas padrão")
    print("• Considere usar autenticação OAuth para maior segurança")





