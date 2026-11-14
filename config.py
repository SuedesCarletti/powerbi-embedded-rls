import os
from dotenv import load_dotenv
import json
import re
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    # ================= CONFIGURAÇÃO SEGURA =================
    # NUNCA mais credenciais hardcoded! Apenas variáveis de ambiente
    
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')  
    TENANT_ID = os.getenv('TENANT_ID')
    
    # Verificação obrigatória de segurança
    if not CLIENT_ID:
        raise ValueError("❌ CLIENT_ID não definido nas variáveis de ambiente!")
    if not CLIENT_SECRET:
        raise ValueError("❌ CLIENT_SECRET não definido nas variáveis de ambiente!")
    if not TENANT_ID:
        raise ValueError("❌ TENANT_ID não definido nas variáveis de ambiente!")
    
    # Power BI Configuration
    POWER_BI_API_URL = "https://api.powerbi.com/v1.0/myorg"
    
    # App Configuration
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("❌ SECRET_KEY não definido nas variáveis de ambiente!")
    
    # ================= WORKSPACE PRINCIPAL =================
    WORKSPACE_ID = os.getenv('WORKSPACE_ID')
    if not WORKSPACE_ID or WORKSPACE_ID in ['SEU_WORKSPACE_ID_AQUI', '']:
        raise ValueError("❌ WORKSPACE_ID não definido ou inválido nas variáveis de ambiente!")
    
    # ================= SISTEMA DE RELATÓRIOS FLEXÍVEL =================

        # Cor corporativa padrão
    CORPORATE_PRIMARY_COLOR = "#002951"  # Azul corporativo escuro
    CORPORATE_BACKGROUND_COLOR = "#002951"  # Mesmo azul como fundo padrão
    
    @staticmethod
    def get_corporate_colors():
        """Retorna paleta de cores corporativas"""
        return {
            "primary": "#002951",        # Azul corporativo principal
            "primary_light": "#0d4a73",  # Azul mais claro
            "primary_dark": "#001a2e",   # Azul mais escuro
            "background": "#002951",     # Fundo padrão
            "background_light": "#f8f9fa", # Fundo claro alternativo
            "text_light": "#ffffff",     # Texto claro para fundos escuros
            "text_dark": "#333333",      # Texto escuro para fundos claros
            "accent": "#0078d4",         # Azul Microsoft (para botões/destaques)
            "success": "#107c10",        # Verde para sucesso
            "warning": "#ff8c00",        # Laranja para avisos
            "error": "#d13438"           # Vermelho para erros
        }
    
    @staticmethod
    def _get_report_names_from_env():
        """
        Descobre automaticamente todos os relatórios configurados nas variáveis de ambiente.
        
        Procura por padrões como:
        - REPORT_ID_EXECUTIVO
        - REPORT_ID_VENDAS
        - REPORT_ID_LOGISTICA
        
        Returns:
            list: Lista de nomes de relatórios encontrados (ex: ['EXECUTIVO', 'VENDAS', 'LOGISTICA'])
        """
        report_names = set()
        
        # Procurar por todas as variáveis que começam com REPORT_ID_
        for key in os.environ.keys():
            if key.startswith('REPORT_ID_'):
                # Extrair o nome do relatório (ex: REPORT_ID_EXECUTIVO -> EXECUTIVO)
                report_name = key[10:]  # Remove 'REPORT_ID_'
                if report_name:  # Só adiciona se não for vazio
                    report_names.add(report_name)
        
        logger.info(f"Relatórios descobertos nas variáveis de ambiente: {sorted(report_names)}")
        return sorted(report_names)
    
    @staticmethod
    def _get_report_config_from_env(report_name):
        """
        ATUALIZADO: Carrega configuração com cor corporativa padrão
        """
        report_id_key = f"REPORT_ID_{report_name}"
        report_id = os.getenv(report_id_key)
        
        if not report_id:
            logger.warning(f"{report_id_key} não encontrado nas variáveis de ambiente")
            return None
        
        # Dataset ID (opcional)
        dataset_id_key = f"DATASET_ID_{report_name}"
        dataset_id = os.getenv(dataset_id_key)
        
        # Workspace ID (opcional, usa principal se não definido)
        workspace_id_key = f"WORKSPACE_ID_{report_name}"
        workspace_id = os.getenv(workspace_id_key, Config.WORKSPACE_ID)
        
        # Metadata (opcional, JSON)
        metadata_key = f"METADATA_{report_name}"
        metadata_json = os.getenv(metadata_key, '{}')
        
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            logger.warning(f"{metadata_key} contém JSON inválido, usando valores padrão")
            metadata = {}
        
  # Definir cor de fundo baseada na categoria ou usar corporativa
        category = metadata.get("category", "outros").lower()
        
        # Cores por categoria, todas baseadas na cor corporativa
        category_colors = {
            "executivo": Config.CORPORATE_PRIMARY_COLOR,     # Azul corporativo
            "gerencial": Config.CORPORATE_PRIMARY_COLOR,     # Azul corporativo  
            "vendas": "#0d4a73",                            # Azul mais claro
            "financeiro": "#f8f9fa",                        # Branco para contraste
            "marketing": "#e3f2fd",                         # Azul muito claro
            "rh": "#f3e5f5",                               # Roxo claro
            "operacional": "#e8f5e8",                       # Verde claro
            "logistica": "#fff3e0",                         # Laranja claro
            "outros": Config.CORPORATE_PRIMARY_COLOR         # Azul corporativo padrão
        }
        
        # Usar cor do metadata ou cor padrão da categoria
        default_background = category_colors.get(category, Config.CORPORATE_PRIMARY_COLOR)
        background_color = metadata.get("background_color", default_background)
        
        # Construir configuração
        config = {
            "name": metadata.get("name", f"Dashboard {report_name.title()}"),
            "report_id": report_id,
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "description": metadata.get("description", f"Relatório {report_name.lower()} da empresa"),
            "category": category,
            "required_roles": metadata.get("required_roles", ["admin", "viewer"]),
            "required_regions": metadata.get("required_regions"),  # None = todas as regiões
            "embed_url": "",  # Preenchido dinamicamente
            "web_url": "",    # Preenchido dinamicamente
            "workspace_name": metadata.get("workspace_name", "Workspace Principal"),
            "background_color": background_color,  # Sempre incluir cor de fundo
            "text_color": "#ffffff" if background_color == Config.CORPORATE_PRIMARY_COLOR else "#333333"  # Cor do texto baseada no fundo
        }
        
        logger.debug(f"Configuração carregada para {report_name}: {config['name']} (Fundo: {background_color})")
        return config    
    @staticmethod
    def get_reports_config():
        """
        Retorna configuração de todos os relatórios.
        
        NOVA FUNCIONALIDADE: Tenta primeiro carregar do sistema flexível (variáveis individuais),
        depois tenta o sistema antigo (REPORTS_CONFIG), e por último usa fallback.
        
        Returns:
            dict: Dicionário com nomes de relatórios como chaves e configurações como valores
        """
        
        # SISTEMA Carregar relatórios individuais das variáveis de ambiente
        report_names = Config._get_report_names_from_env()
        
        if report_names:
            logger.info(f"Usando sistema flexível de configuração - {len(report_names)} relatórios")
            
            reports_config = {}
            for report_name in report_names:
                config = Config._get_report_config_from_env(report_name)
                if config:
                    # Usar nome do relatório em minúsculas como chave
                    key = report_name.lower()
                    reports_config[key] = config
                    
            if reports_config:
                logger.info(f"{len(reports_config)} relatórios carregados via sistema flexível")
                return reports_config
        
        # SISTEMA ANTIGO: Tentar carregar REPORTS_CONFIG (compatibilidade)
        reports_json = os.getenv('REPORTS_CONFIG')
        if reports_json:
            try:
                logger.info("Usando sistema legado REPORTS_CONFIG")
                return json.loads(reports_json)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar REPORTS_CONFIG: {e}")
        
        # FALLBACK: Sistema básico baseado em REPORT_ID/WORKSPACE_ID principais
        logger.warning("Nenhum sistema de relatórios configurado, usando fallback básico")
        
        # Verificar se pelo menos as variáveis básicas existem
        basic_report_id = os.getenv('REPORT_ID')
        if basic_report_id and basic_report_id not in ['SEU_REPORT_ID_AQUI', '']:
            return {
                "principal": {
                    "name": "Dashboard Principal",
                    "report_id": basic_report_id,
                    "workspace_id": Config.WORKSPACE_ID,
                    "dataset_id": os.getenv('DATASET_ID', ''),
                    "description": "Dashboard principal com métricas da empresa",
                    "category": "executivo",
                    "required_roles": ["admin", "viewer"],
                    "required_regions": None,
                    "embed_url": "",
                    "web_url": "",
                    "workspace_name": "Workspace Principal"
                }
            }
        
        # Se chegou até aqui, não há relatórios configurados
        logger.error("Nenhum relatório configurado em nenhum sistema!")
        return {}
    
    @staticmethod
    def get_report_by_name(report_name):
        """
        Retorna configuração de um relatório específico pelo nome.
        
        Args:
            report_name (str): Nome do relatório (ex: 'executivo', 'vendas')
            
        Returns:
            dict: Configuração do relatório ou None se não encontrado
        """
        reports = Config.get_reports_config()
        return reports.get(report_name.lower())
    
    @staticmethod
    def get_report_by_id(report_id):
        """
        MÉTODO LEGADO: Mantido para compatibilidade.
        Tenta encontrar relatório pelo report_id (GUID do Power BI).
        
        Args:
            report_id (str): ID do relatório no Power BI
            
        Returns:
            dict: Configuração do relatório ou None se não encontrado
        """
        reports = Config.get_reports_config()
        
        # Procurar em todas as configurações
        for report_name, config in reports.items():
            if config.get('report_id') == report_id:
                return config
        
        logger.warning(f"Relatório com ID {report_id} não encontrado")
        return None
    
    @staticmethod
    def get_reports_for_user(user_roles, user_region):
        """
        Retorna relatórios que o usuário pode acessar baseado em roles e região.
        
        Args:
            user_roles (list): Lista de roles do usuário
            user_region (str): Região do usuário
            
        Returns:
            dict: Relatórios acessíveis
        """
        reports = Config.get_reports_config()
        accessible_reports = {}
        
        for report_name, config in reports.items():
            # Verificar roles
            required_roles = config.get('required_roles', [])
            if required_roles and not any(role in user_roles for role in required_roles):
                continue
            
            # Verificar região
            required_regions = config.get('required_regions')
            if required_regions and user_region not in required_regions:
                continue
            
            accessible_reports[report_name] = config
        
        logger.debug(f"Usuário (roles: {user_roles}, região: {user_region}) pode acessar {len(accessible_reports)} relatórios")
        return accessible_reports
    
    @staticmethod
    def get_categories():
        """Retorna categorias de relatórios disponíveis"""
        reports = Config.get_reports_config()
        categories = set()
        
        for config in reports.values():
            category = config.get('category', 'outros')
            categories.add(category)
        
        return sorted(list(categories))

    # ================= VALIDAÇÃO DE SEGURANÇA =================
    
    @staticmethod
    def validate_config():
        """Valida se a configuração está correta e segura"""
        issues = []
        
        # Verificar credenciais obrigatórias
        required_env_vars = ['CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID', 'SECRET_KEY', 'WORKSPACE_ID']
        
        for var in required_env_vars:
            value = os.getenv(var)
            if not value:
                issues.append(f"{var} não está definido nas variáveis de ambiente")
            elif var in ['CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID'] and len(value) < 10:
                issues.append(f"{var} parece ser inválido (muito curto)")
        
        # Verificar se não são placeholders
        placeholder_patterns = ['SEU_', 'AQUI', 'CHANGE', 'TODO', 'EXEMPLO']
        for var in required_env_vars:
            value = os.getenv(var, '')
            if any(pattern in value.upper() for pattern in placeholder_patterns):
                issues.append(f"{var} ainda contém placeholder - configure com valor real")
        
        # Verificar relatórios
        try:
            reports = Config.get_reports_config()
            if not reports:
                issues.append("Nenhum relatório configurado em nenhum sistema")
            else:
                for report_name, config in reports.items():
                    if not config.get('report_id'):
                        issues.append(f"Relatório '{report_name}': report_id ausente")
                    
                    if not config.get('workspace_id'):
                        issues.append(f"Relatório '{report_name}': workspace_id ausente")
                    
                    if not config.get('name'):
                        issues.append(f"Relatório '{report_name}': nome ausente")
                        
                    # Verificar se metadata JSON está válido
                    metadata_key = f"METADATA_{report_name.upper()}"
                    if os.getenv(metadata_key):
                        try:
                            json.loads(os.getenv(metadata_key))
                        except json.JSONDecodeError:
                            issues.append(f"Relatório '{report_name}': {metadata_key} contém JSON inválido")
                            
        except Exception as e:
            issues.append(f"Erro ao carregar configuração de relatórios: {e}")
        
        return issues

    # ================= CONFIGURAÇÕES AVANÇADAS =================
    
    # Cache de tokens (em produção, use Redis)
    CACHE_TOKENS = os.getenv('CACHE_TOKENS', 'true').lower() == 'true'
    TOKEN_CACHE_DURATION = int(os.getenv('TOKEN_CACHE_DURATION', '3000'))
    
    # Configurações de segurança
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hora
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '3'))
    
    # Configurações de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Configurações específicas do Power BI
    EMBED_TOKEN_TIMEOUT = int(os.getenv('EMBED_TOKEN_TIMEOUT', '60'))
    ENABLE_RLS = os.getenv('ENABLE_RLS', 'false').lower() == 'true'
    
    # ================= UTILITÁRIOS DE SEGURANÇA =================
    
    @staticmethod
    def get_masked_config():
        """Retorna configuração com valores sensíveis mascarados (para logs/debug)"""
        masked = {
            "CLIENT_ID": Config.CLIENT_ID[:8] + "..." if Config.CLIENT_ID else "NÃO DEFINIDO",
            "CLIENT_SECRET": "****" if Config.CLIENT_SECRET else "NÃO DEFINIDO",
            "TENANT_ID": Config.TENANT_ID if Config.TENANT_ID else "NÃO DEFINIDO",
            "WORKSPACE_ID": Config.WORKSPACE_ID[:8] + "..." if Config.WORKSPACE_ID else "NÃO DEFINIDO",
            "SECRET_KEY": "****" if Config.SECRET_KEY else "NÃO DEFINIDO"
        }
        
        # Adicionar informações sobre relatórios
        reports = Config.get_reports_config()
        masked["REPORTS_COUNT"] = len(reports)
        masked["REPORTS_NAMES"] = list(reports.keys())
        
        return masked
    
    @staticmethod
    def is_production():
        """Verifica se está em ambiente de produção"""
        return os.getenv('RAILWAY_ENVIRONMENT') is not None or os.getenv('FLASK_ENV') == 'production'
    
    @staticmethod
    def list_env_reports():
        """
        Lista todos os relatórios configurados nas variáveis de ambiente para debug.
        
        Returns:
            dict: Informações sobre os relatórios encontrados
        """
        report_names = Config._get_report_names_from_env()
        info = {
            "system_type": "flexible" if report_names else "legacy",
            "reports_found": len(report_names),
            "report_names": report_names,
            "details": {}
        }
        
        for report_name in report_names:
            config = Config._get_report_config_from_env(report_name)
            if config:
                info["details"][report_name] = {
                    "name": config["name"],
                    "category": config["category"],
                    "has_dataset": bool(config.get("dataset_id")),
                    "has_custom_workspace": config["workspace_id"] != Config.WORKSPACE_ID,
                    "required_roles": config.get("required_roles", [])
                }
        
        return info
    
    @staticmethod
    def test_config():
        """Testa se a configuração está funcionando"""
        print("TESTE DE CONFIGURAÇÃO FLEXÍVEL")
        print("=" * 60)
        
        # Teste 1: Validação de segurança
        issues = Config.validate_config()
        if issues:
            print("Problemas de segurança encontrados:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("Validação de segurança OK")
        
        # Teste 2: Mostrar configuração mascarada
        print(f"\nConfiguração mascarada:")
        masked_config = Config.get_masked_config()
        for key, value in masked_config.items():
            print(f"   {key}: {value}")
        
        # Teste 3: Sistema de relatórios
        print(f"\nSistema de relatórios:")
        env_info = Config.list_env_reports()
        print(f"   Tipo: {env_info['system_type']}")
        print(f"   Relatórios encontrados: {env_info['reports_found']}")
        
        if env_info['details']:
            print(f"   Detalhes:")
            for report_name, details in env_info['details'].items():
                print(f"     • {report_name}: {details['name']} ({details['category']})")
        
        # Teste 4: Ambiente
        env_type = "PRODUÇÃO" if Config.is_production() else "DESENVOLVIMENTO"
        print(f"\nAmbiente detectado: {env_type}")
        
        # Teste 5: Relatórios finais carregados
        try:
            reports = Config.get_reports_config()
            print(f"\nRelatórios carregados: {len(reports)}")
            
            for report_name, config in reports.items():
                print(f"   • {report_name}: {config['name']} ({config.get('category', 'N/A')})")
                print(f"     - Report ID: {config.get('report_id', 'N/A')[:8]}...")
                print(f"     - Workspace: {config.get('workspace_id', 'N/A')[:8]}...")
                print(f"     - Roles: {config.get('required_roles', [])}")
                
        except Exception as e:
            print(f"\nErro ao carregar relatórios: {e}")
        
        print(f"\n" + "=" * 60)
        
        return len(issues) == 0

# Validação automática na importação (apenas em desenvolvimento)
if __name__ != "__main__" and not Config.is_production():
    try:
        issues = Config.validate_config()
        if issues:
            logger.warning("AVISOS DE CONFIGURAÇÃO:")
            for issue in issues:
                logger.warning(f"   • {issue}")
        
        # Log do sistema de relatórios detectado
        env_info = Config.list_env_reports()
        logger.info(f"Sistema de relatórios: {env_info['system_type']} ({env_info['reports_found']} relatórios)")
        
    except Exception as e:
        logger.error(f"Erro na validação automática: {e}")

# Execução de teste se chamado diretamente
if __name__ == "__main__":
    Config.test_config()

