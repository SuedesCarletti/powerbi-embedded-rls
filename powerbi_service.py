import requests
from config import Config
import json
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PowerBIService:
    def __init__(self):
        self.config = Config()
        self.access_token = None
        self.token_expires = None
        
        # Debug: Verificar se as variáveis estão configuradas
        logger.info(f"CLIENT_ID: {self.config.CLIENT_ID[:10]}...")
        logger.info(f"TENANT_ID: {self.config.TENANT_ID}")
        logger.info(f"WORKSPACE_ID Principal: {self.config.WORKSPACE_ID}")
        
        # Verificar se as variáveis essenciais estão definidas
        if not all([self.config.CLIENT_ID, self.config.CLIENT_SECRET, self.config.TENANT_ID]):
            raise ValueError("❌ Credenciais do Service Principal não estão configuradas!")
        
        # Log do sistema de relatórios
        reports = Config.get_reports_config()
        logger.info(f"Sistema de relatórios: {len(reports)} relatórios configurados")
        for name, config in reports.items():
            logger.info(f"   • {name}: {config['name']} (Workspace: {config['workspace_id'][:8]}...)")
    
    def get_access_token(self, force_refresh=False):
        """Obtém token usando Service Principal (client_credentials)"""
        if not force_refresh and self.access_token and self.token_expires and datetime.now() < self.token_expires:
            logger.debug("Usando token em cache")
            return self.access_token
        
        logger.info("Obtendo novo access token com Service Principal...")
        
        token_url = f'https://login.microsoftonline.com/{self.config.TENANT_ID}/oauth2/v2.0/token'
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }
        
        try:
            logger.debug(f"Fazendo requisição para: {token_url}")
            response = requests.post(token_url, data=data, timeout=30)
            
            logger.debug(f"Status da requisição: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Erro na requisição: {response.text}")
                raise Exception(f"Failed to get token. Status: {response.status_code}, Response: {response.text}")
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logger.info("Token obtido com sucesso!")
            logger.debug(f"Token expira em: {self.token_expires}")
            
            return self.access_token
            
        except requests.exceptions.Timeout:
            logger.error("Timeout ao obter token")
            raise Exception("Timeout getting access token")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao obter token: {e}")
            raise Exception(f"Network error getting token: {e}")
        except Exception as e:
            logger.error(f"Erro geral ao obter token: {e}")
            raise Exception(f"Failed to get token: {e}")
    
    def get_headers(self):
        """Retorna headers com token atualizado"""
        token = self.get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    # ================= MÉTODOS PARA RELATÓRIOS ESPECÍFICOS =================
    
    def get_report_info_by_id(self, workspace_id, report_id):
        """
        Obtém informações de um relatório específico por workspace e report ID.
        
        Args:
            workspace_id (str): ID do workspace
            report_id (str): ID do relatório
            
        Returns:
            dict: Informações do relatório
        """
        url = f"{self.config.POWER_BI_API_URL}/groups/{workspace_id}/reports/{report_id}"
        
        try:
            logger.info(f"Obtendo info do relatório {report_id[:8]}... no workspace {workspace_id[:8]}...")
            
            headers = self.get_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            logger.debug(f"Status da info do relatório: {response.status_code}")
            
            if response.status_code == 200:
                report_info = response.json()
                logger.info(f"Informações obtidas: {report_info.get('name', 'N/A')}")
                
                # Log adicional para debug
                logger.debug(f"Report ID: {report_info.get('id')}")
                logger.debug(f"Embed URL: {report_info.get('embedUrl', 'N/A')}")
                logger.debug(f"Dataset ID: {report_info.get('datasetId', 'N/A')}")
                
                return report_info
            elif response.status_code == 401:
                logger.warning("Token expirado, renovando...")
                self.get_access_token(force_refresh=True)
                headers = self.get_headers()
                
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    report_info = response.json()
                    logger.info("Informações do relatório obtidas após renovação!")
                    return report_info
                else:
                    error_detail = response.text
                    logger.error(f"Erro ao obter info do relatório após renovação: {error_detail}")
                    raise Exception(f"Failed to get report info. Status: {response.status_code}, Response: {error_detail}")
            else:
                error_detail = response.text
                logger.error(f"Erro ao obter info do relatório: {error_detail}")
                raise Exception(f"Failed to get report info. Status: {response.status_code}, Response: {error_detail}")
                
        except Exception as e:
            logger.error(f"Erro ao obter info do relatório {report_id}: {e}")
            raise
    
    def get_embed_token_for_report(self, workspace_id, report_id, dataset_id=None, user_identity=None):
        """
        Gera embed token para um relatório específico.
        
        Args:
            workspace_id (str): ID do workspace
            report_id (str): ID do relatório
            dataset_id (str, optional): ID do dataset (para RLS)
            user_identity (dict, optional): Identidade do usuário para RLS
            
        Returns:
            dict: Dados do embed token
        """
        url = f"{self.config.POWER_BI_API_URL}/groups/{workspace_id}/reports/{report_id}/GenerateToken"
        
        # Payload básico
        payload = {
            "accessLevel": "View",
            "allowSaveAs": False
        }
        
        # =================== RLS (ROW-LEVEL SECURITY) ===================
        # Adicionar identities apenas se RLS estiver habilitado e user_identity fornecido
        if Config.ENABLE_RLS and user_identity and dataset_id:
            logger.info(f"Aplicando RLS para usuário: {user_identity.get('username')}")
            
            payload["identities"] = [{
                "username": user_identity["username"],
                "roles": user_identity.get("roles", []),
                "datasets": [dataset_id]
            }]
            
            logger.debug(f"RLS configurado: {payload['identities']}")
        elif user_identity:
            logger.info(f"Token para usuário: {user_identity.get('username')} (sem RLS)")
        
        try:
            logger.info(f"Gerando embed token para relatório {report_id[:8]}...")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            headers = self.get_headers()
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            logger.debug(f"Status da embed token: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info("Embed token gerado com sucesso!")
                logger.debug(f"Token expira em: {token_data.get('expiration')}")
                return {
                    "token": token_data["token"],
                    "tokenId": token_data["tokenId"],
                    "expiration": token_data["expiration"]
                }
            elif response.status_code == 401:
                logger.warning("Token expirado, renovando...")
                self.get_access_token(force_refresh=True)
                headers = self.get_headers()
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    token_data = response.json()
                    logger.info("Embed token gerado com sucesso após renovação!")
                    return {
                        "token": token_data["token"],
                        "tokenId": token_data["tokenId"],
                        "expiration": token_data["expiration"]
                    }
                else:
                    error_detail = response.text
                    logger.error(f"Erro ao gerar embed token após renovação: {error_detail}")
                    raise Exception(f"Failed to get embed token. Status: {response.status_code}, Response: {error_detail}")
            else:
                error_detail = response.text
                logger.error(f"Erro ao gerar embed token: {error_detail}")
                
                # Log específico para erros comuns
                if "shouldn't have effective identity" in error_detail:
                    logger.error("DICA: Este relatório não suporta RLS. Desabilite ENABLE_RLS ou configure RLS no Power BI.")
                elif "doesn't exist" in error_detail:
                    logger.error("DICA: Verifique se o REPORT_ID e WORKSPACE_ID estão corretos.")
                
                raise Exception(f"Failed to get embed token. Status: {response.status_code}, Response: {error_detail}")
                
        except Exception as e:
            logger.error(f"Erro geral ao gerar token para {report_id}: {e}")
            raise
    
    # ================= MÉTODOS DE CONVENIÊNCIA PARA RELATÓRIOS POR NOME =================
    
    def get_embed_config_for_report_name(self, report_name, user_identity=None):
        """
        Gera configuração completa de embed para um relatório pelo nome.
        
        Args:
            report_name (str): Nome do relatório (ex: 'executivo', 'vendas')
            user_identity (dict, optional): Identidade do usuário para RLS
            
        Returns:
            dict: Configuração completa para embed
        """
        # Obter configuração do relatório
        report_config = Config.get_report_by_name(report_name)
        if not report_config:
            raise ValueError(f"Relatório '{report_name}' não encontrado na configuração")
        
        workspace_id = report_config['workspace_id']
        report_id = report_config['report_id']
        dataset_id = report_config.get('dataset_id')
        
        logger.info(f"Gerando embed para relatório '{report_config['name']}' ({report_name})")
        logger.debug(f"   Workspace: {workspace_id[:8]}... | Report: {report_id[:8]}... | Dataset: {dataset_id[:8] if dataset_id else 'N/A'}...")
        
        # Obter informações do relatório
        report_info = self.get_report_info_by_id(workspace_id, report_id)
        
        # Gerar embed token
        embed_data = self.get_embed_token_for_report(workspace_id, report_id, dataset_id, user_identity)
        
        # Retornar configuração completa
        config = {
            "type": "report",
            "id": report_info["id"],
            "embedUrl": report_info["embedUrl"],
            "accessToken": embed_data["token"],
            "tokenType": 0,  # Embed token
            "permissions": 1,  # View permission
            "settings": {
                "filterPaneEnabled": False,
                "navContentPaneEnabled": True,
                "hideErrors": True
            }
        }
        
        logger.info(f"Configuração de embed para '{report_name}' gerada com sucesso!")
        return config
    
    # ================= MÉTODOS LEGADOS (COMPATIBILIDADE) =================
    
    def get_embed_token(self, user_identity=None):
        """
        MÉTODO LEGADO: Gera embed token para relatório principal.
        Mantido para compatibilidade com código antigo.
        """
        # Tentar usar relatório principal configurado no .env
        principal_report_id = os.getenv('REPORT_ID')
        if principal_report_id and principal_report_id not in ['SEU_REPORT_ID_AQUI', '']:
            return self.get_embed_token_for_report(
                self.config.WORKSPACE_ID, 
                principal_report_id, 
                os.getenv('DATASET_ID'),
                user_identity
            )
        
        # Fallback: usar primeiro relatório configurado
        reports = Config.get_reports_config()
        if reports:
            first_report_name = list(reports.keys())[0]
            first_report_config = reports[first_report_name]
            
            logger.warning(f"Usando relatório '{first_report_name}' como fallback para método legado")
            
            return self.get_embed_token_for_report(
                first_report_config['workspace_id'],
                first_report_config['report_id'],
                first_report_config.get('dataset_id'),
                user_identity
            )
        
        raise ValueError("❌ Nenhum relatório configurado para método legado")
    
    def get_report_info(self):
        """
        MÉTODO LEGADO: Obtém informações do relatório principal.
        Mantido para compatibilidade com código antigo.
        """
        principal_report_id = os.getenv('REPORT_ID')
        if principal_report_id and principal_report_id not in ['SEU_REPORT_ID_AQUI', '']:
            return self.get_report_info_by_id(self.config.WORKSPACE_ID, principal_report_id)
        
        # Fallback: usar primeiro relatório configurado
        reports = Config.get_reports_config()
        if reports:
            first_report_name = list(reports.keys())[0]
            first_report_config = reports[first_report_name]
            
            logger.warning(f"Usando relatório '{first_report_name}' como fallback para método legado")
            
            return self.get_report_info_by_id(
                first_report_config['workspace_id'],
                first_report_config['report_id']
            )
        
        raise ValueError("❌ Nenhum relatório configurado para método legado")
    
    def get_embed_config(self, user_identity=None):
        """
        MÉTODO LEGADO: Retorna configuração completa de embed.
        Mantido para compatibilidade com código antigo.
        """
        try:
            # Obter informações do relatório
            report_info = self.get_report_info()
            
            # Gerar embed token
            embed_data = self.get_embed_token(user_identity)
            
            # Retornar configuração completa
            return {
                "type": "report",
                "id": report_info["id"],
                "embedUrl": report_info["embedUrl"],
                "accessToken": embed_data["token"],
                "tokenType": 0,  # Embed token
                "permissions": 1,  # View permission
                "settings": {
                    "filterPaneEnabled": False,
                    "navContentPaneEnabled": True,
                    "hideErrors": True
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar configuração de embed legada: {e}")
            raise
    
    # ================= MÉTODOS UTILITÁRIOS =================
    
    def list_workspaces(self):
        """Lista todos os workspaces acessíveis"""
        url = f"{self.config.POWER_BI_API_URL}/groups"
        
        try:
            logger.info("Listando workspaces acessíveis...")
            headers = self.get_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                workspaces = response.json().get('value', [])
                logger.info(f"Encontrados {len(workspaces)} workspaces")
                return workspaces
            else:
                logger.error(f"Erro ao listar workspaces: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao listar workspaces: {e}")
            return []
    
    def list_reports_in_workspace(self, workspace_id):
        """Lista relatórios em um workspace específico"""
        url = f"{self.config.POWER_BI_API_URL}/groups/{workspace_id}/reports"
        
        try:
            logger.info(f"Listando relatórios no workspace {workspace_id[:8]}...")
            headers = self.get_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                reports = response.json().get('value', [])
                logger.info(f"Encontrados {len(reports)} relatórios")
                return reports
            else:
                logger.error(f"Erro ao listar relatórios: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao listar relatórios do workspace: {e}")
            return []
    
    def test_connection(self):
        """Testa se a conexão com Power BI está funcionando"""
        try:
            logger.info("Testando conexão com Power BI...")
            
            # Testar obtenção de token
            token = self.get_access_token()
            if not token:
                return {"status": "error", "message": "Não foi possível obter token"}
            
            # Testar listagem de workspaces
            workspaces = self.list_workspaces()
            
            # Testar acesso aos relatórios configurados
            reports = Config.get_reports_config()
            tested_reports = []
            
            for report_name, config in reports.items():
                try:
                    report_info = self.get_report_info_by_id(
                        config['workspace_id'], 
                        config['report_id']
                    )
                    tested_reports.append({
                        "name": report_name,
                        "display_name": config['name'],
                        "status": "ok"
                    })
                except Exception as e:
                    tested_reports.append({
                        "name": report_name,
                        "display_name": config['name'],
                        "status": f"error: {str(e)}"
                    })
            
            logger.info("Teste de conexão com Power BI concluído!")
            return {
                "status": "success",
                "message": "Conexão OK",
                "workspaces_count": len(workspaces),
                "reports_configured": len(reports),
                "reports_tested": tested_reports
            }
            
        except Exception as e:
            logger.error(f"Erro no teste de conexão: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_system_info(self):
        """Retorna informações do sistema para debug"""
        try:
            reports = Config.get_reports_config()
            env_info = Config.list_env_reports()
            
            return {
                "powerbi_service": "initialized",
                "token_cached": self.access_token is not None,
                "token_expires": str(self.token_expires) if self.token_expires else None,
                "reports_system": env_info["system_type"],
                "reports_count": len(reports),
                "reports_list": [
                    {
                        "name": name,
                        "display_name": config["name"],
                        "category": config.get("category", "N/A"),
                        "workspace": config["workspace_id"][:8] + "...",
                        "report_id": config["report_id"][:8] + "..."
                    }
                    for name, config in reports.items()
                ]
            }
        except Exception as e:
            return {"error": str(e)}
