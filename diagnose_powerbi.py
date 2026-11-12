#!/usr/bin/env python3
"""
Script de diagnóstico completo para Power BI Embedded
Executa uma série de testes para identificar problemas de configuração
"""

import os
import sys
import requests
import json
from datetime import datetime
import time

class PowerBIDiagnostics:
    def __init__(self):
        self.tenant_id = os.getenv('TENANT_ID', '00000000-0000-0000-0000-000000000004')
        self.client_id = os.getenv('CLIENT_ID', '00000000-0000-0000-0000-000000000026')
        self.client_secret = os.getenv('CLIENT_SECRET', 'jc58Q~WH3qOmPLB83zXYQ~ehYLR1.oByb7E3TclQ')
        self.workspace_id = os.getenv('WORKSPACE_ID', '00000000-0000-0000-0000-000000000027')
        self.report_id = os.getenv('REPORT_ID', '00000000-0000-0000-0000-000000000028')
        self.dataset_id = os.getenv('DATASET_ID')
        
        self.token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        self.powerbi_api = 'https://api.powerbi.com/v1.0/myorg'
        
        self.access_token = None
        self.test_results = []
        
    def print_header(self, title):
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)
        
    def test_step(self, step_name):
        print(f"\n{step_name}...")
        
    def success(self, message):
        print(f"   {message}")
        self.test_results.append(("SUCCESS", message))
        
    def warning(self, message):
        print(f"    {message}")
        self.test_results.append(("WARNING", message))
        
    def error(self, message):
        print(f"   {message}")
        self.test_results.append(("ERROR", message))
        
    def info(self, message):
        print(f"   ℹ {message}")
        
    def test_environment_variables(self):
        """Teste 1: Verificar variáveis de ambiente"""
        self.test_step("TESTE 1: Verificando variáveis de ambiente")
        
        vars_ok = True
        
        # Verificar cada variável
        if not self.client_id:
            self.error("CLIENT_ID não está definido")
            vars_ok = False
        else:
            self.success(f"CLIENT_ID: {self.client_id[:10]}...")
            
        if not self.client_secret:
            self.error("CLIENT_SECRET não está definido")
            vars_ok = False
        else:
            self.success(f"CLIENT_SECRET: ****")
            
        if not self.tenant_id:
            self.error("TENANT_ID não está definido")
            vars_ok = False
        else:
            self.success(f"TENANT_ID: {self.tenant_id}")
            
        if not self.workspace_id or self.workspace_id == "SEU_WORKSPACE_ID_AQUI":
            self.error("WORKSPACE_ID não está configurado corretamente")
            vars_ok = False
        else:
            self.success(f"WORKSPACE_ID: {self.workspace_id}")
            
        if not self.report_id or self.report_id == "SEU_REPORT_ID_AQUI":
            self.error("REPORT_ID não está configurado corretamente")
            vars_ok = False
        else:
            self.success(f"REPORT_ID: {self.report_id}")
            
        if not self.dataset_id or self.dataset_id == "SEU_DATASET_ID_AQUI":
            self.warning("DATASET_ID não está configurado (necessário apenas para RLS)")
        else:
            self.success(f"DATASET_ID: {self.dataset_id}")
            
        return vars_ok
        
    def test_token_acquisition(self):
        """Teste 2: Obter access token"""
        self.test_step("TESTE 2: Obtendo Access Token do Azure AD")
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }
        
        try:
            self.info(f"Endpoint: {self.token_url}")
            self.info("Método: POST")
            self.info("Grant Type: client_credentials")
            
            response = requests.post(self.token_url, data=data, timeout=30)
            
            self.info(f"Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 0)
                
                self.success(f"Token obtido com sucesso!")
                self.info(f"Token expira em: {expires_in} segundos")
                self.info(f"Token começa com: {self.access_token[:20]}...")
                
                return True
            else:
                self.error(f"Falha ao obter token: HTTP {response.status_code}")
                
                # Tentar decodificar erro
                try:
                    error_data = response.json()
                    self.error(f"Erro: {error_data.get('error', 'Unknown')}")
                    self.error(f"Descrição: {error_data.get('error_description', 'N/A')}")
                except:
                    self.error(f"Resposta: {response.text[:200]}")
                    
                return False
                
        except requests.exceptions.Timeout:
            self.error("Timeout ao conectar com Azure AD")
            return False
        except Exception as e:
            self.error(f"Erro ao obter token: {str(e)}")
            return False
            
    def test_workspace_access(self):
        """Teste 3: Verificar acesso ao workspace"""
        self.test_step("TESTE 3: Verificando acesso ao Workspace")
        
        if not self.access_token:
            self.error("Token não disponível - pulando teste")
            return False
            
        url = f"{self.powerbi_api}/groups/{self.workspace_id}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            self.info(f"URL: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            self.info(f"Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                workspace_data = response.json()
                self.success(f"Workspace acessível: {workspace_data.get('name', 'N/A')}")
                self.info(f"Tipo: {workspace_data.get('type', 'N/A')}")
                self.info(f"Estado: {workspace_data.get('state', 'N/A')}")
                return True
                
            elif response.status_code == 401:
                self.error("Não autorizado - Token inválido ou sem permissão")
                self.info("Verifique se o Service Principal tem acesso ao workspace")
                return False
                
            elif response.status_code == 404:
                self.error("Workspace não encontrado")
                self.info(f"Workspace ID: {self.workspace_id}")
                return False
                
            else:
                self.error(f"Erro ao acessar workspace: HTTP {response.status_code}")
                self.error(f"Resposta: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.error(f"Erro ao verificar workspace: {str(e)}")
            return False
            
    def test_report_access(self):
        """Teste 4: Verificar acesso ao relatório"""
        self.test_step("TESTE 4: Verificando acesso ao Relatório")
        
        if not self.access_token:
            self.error("Token não disponível - pulando teste")
            return False
            
        url = f"{self.powerbi_api}/groups/{self.workspace_id}/reports/{self.report_id}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            self.info(f"URL: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            self.info(f"Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                report_data = response.json()
                self.success(f"Relatório acessível: {report_data.get('name', 'N/A')}")
                self.info(f"Dataset ID: {report_data.get('datasetId', 'N/A')}")
                self.info(f"Embed URL: {report_data.get('embedUrl', 'N/A')[:50]}...")
                
                # Salvar dataset ID se não estiver configurado
                if report_data.get('datasetId') and not self.dataset_id:
                    self.warning(f"Dataset ID descoberto: {report_data['datasetId']}")
                    self.info("Adicione ao seu .env: DATASET_ID=" + report_data['datasetId'])
                    
                return True
                
            elif response.status_code == 401:
                self.error("Não autorizado - Token inválido ou sem permissão")
                return False
                
            elif response.status_code == 404:
                self.error("Relatório não encontrado")
                self.info(f"Report ID: {self.report_id}")
                return False
                
            else:
                self.error(f"Erro ao acessar relatório: HTTP {response.status_code}")
                self.error(f"Resposta: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.error(f"Erro ao verificar relatório: {str(e)}")
            return False
            
    def test_embed_token_generation(self):
        """Teste 5: Gerar embed token"""
        self.test_step("TESTE 5: Gerando Embed Token")
        
        if not self.access_token:
            self.error("Token não disponível - pulando teste")
            return False
            
        url = f"{self.powerbi_api}/groups/{self.workspace_id}/reports/{self.report_id}/GenerateToken"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "accessLevel": "View",
            "allowSaveAs": False
        }
        
        try:
            self.info(f"URL: {url}")
            self.info(f"Payload: {json.dumps(payload)}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            self.info(f"Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                embed_data = response.json()
                self.success("Embed token gerado com sucesso!")
                self.info(f"Token ID: {embed_data.get('tokenId', 'N/A')}")
                self.info(f"Expira em: {embed_data.get('expiration', 'N/A')}")
                return True
                
            elif response.status_code == 401:
                self.error("Não autorizado - Token inválido ou sem permissão")
                return False
                
            elif response.status_code == 400:
                self.error("Requisição inválida")
                self.error(f"Resposta: {response.text}")
                return False
                
            else:
                self.error(f"Erro ao gerar embed token: HTTP {response.status_code}")
                self.error(f"Resposta: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.error(f"Erro ao gerar embed token: {str(e)}")
            return False
            
    def test_permissions(self):
        """Teste 6: Verificar permissões do Service Principal"""
        self.test_step("TESTE 6: Verificando Permissões")
        
        if not self.access_token:
            self.error("Token não disponível - pulando teste")
            return False
            
        # Listar todos os workspaces acessíveis
        url = f"{self.powerbi_api}/groups"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                workspaces = response.json().get('value', [])
                self.success(f"Service Principal tem acesso a {len(workspaces)} workspace(s)")
                
                for ws in workspaces:
                    self.info(f"  - {ws['name']} ({ws['id']})")
                    
                # Verificar se o workspace configurado está na lista
                workspace_found = any(ws['id'].upper() == self.workspace_id.upper() for ws in workspaces)
                
                if workspace_found:
                    self.success(f"Workspace configurado está acessível")
                else:
                    self.error(f"Workspace configurado ({self.workspace_id}) NÃO está na lista!")
                    self.info("Adicione o Service Principal como Admin/Member no workspace")
                    
                return workspace_found
                
            else:
                self.error(f"Erro ao listar workspaces: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.error(f"Erro ao verificar permissões: {str(e)}")
            return False
            
    def run_diagnostics(self):
        """Executa todos os testes de diagnóstico"""
        self.print_header("DIAGNÓSTICO POWER BI EMBEDDED")
        
        print(f"\nData/Hora: {datetime.now()}")
        print(f"Ambiente: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
        print(f"Python: {sys.version.split()[0]}")
        
        # Executar testes
        tests = [
            ("Variáveis de Ambiente", self.test_environment_variables),
            ("Obtenção de Token", self.test_token_acquisition),
            ("Acesso ao Workspace", self.test_workspace_access),
            ("Acesso ao Relatório", self.test_report_access),
            ("Geração de Embed Token", self.test_embed_token_generation),
            ("Permissões", self.test_permissions)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                
                if not result:
                    self.warning(f"Parando testes devido a falha em: {test_name}")
                    break
                    
            except Exception as e:
                self.error(f"Erro não tratado em {test_name}: {str(e)}")
                results.append((test_name, False))
                break
                
        # Resumo final
        self.print_header("RESUMO DO DIAGNÓSTICO")
        
        total_tests = len(results)
        passed_tests = sum(1 for _, result in results if result)
        
        print(f"\nTestes executados: {total_tests}")
        print(f"Testes aprovados: {passed_tests}")
        print(f"Testes falhados: {total_tests - passed_tests}")
        
        print("\nResultados por teste:")
        for test_name, result in results:
            icon = "✅" if result else "❌"
            print(f"  {icon} {test_name}")
            
        # Recomendações
        self.print_header("RECOMENDAÇÕES")
        
        errors_count = sum(1 for status, _ in self.test_results if status == "ERROR")
        warnings_count = sum(1 for status, _ in self.test_results if status == "WARNING")
        
        if errors_count > 0:
            print("\nErros encontrados que precisam ser corrigidos:")
            for status, message in self.test_results:
                if status == "ERROR":
                    print(f"  • {message}")
                    
        if warnings_count > 0:
            print("\n Avisos que podem ser melhorados:")
            for status, message in self.test_results:
                if status == "WARNING":
                    print(f"  • {message}")
                    
        if passed_tests == total_tests:
            print("\nTODOS OS TESTES PASSARAM!")
            print("Sua configuração está correta. Se ainda houver problemas,")
            print("verifique os logs da aplicação Flask para mais detalhes.")
        else:
            print("\nPRÓXIMOS PASSOS:")
            
            if "Token" in str(self.test_results) and "ERROR" in str(self.test_results):
                print("1. Verifique se as credenciais do Service Principal estão corretas")
                print("2. Confirme que o Service Principal está ativo no Azure AD")
                
            if "Workspace" in str(self.test_results) and "ERROR" in str(self.test_results):
                print("1. No Power BI Service, vá para o workspace")
                print("2. Clique em 'Manage access' ou 'Gerenciar acesso'")
                print("3. Adicione o Service Principal como Admin ou Member")
                print(f"   App ID: {self.client_id}")
                
            if "Relatório" in str(self.test_results) and "ERROR" in str(self.test_results):
                print("1. Verifique se o relatório existe no workspace")
                print("2. Confirme que o Report ID está correto")
                print("3. Certifique-se de que o relatório foi publicado")
                
        print("\n" + "="*60)
        
if __name__ == "__main__":
    diagnostics = PowerBIDiagnostics()
    diagnostics.run_diagnostics()
