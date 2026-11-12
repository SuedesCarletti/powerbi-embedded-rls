#!/usr/bin/env python3
"""
Script para configurar múltiplos relatórios no Power BI Embedded
Descobre automaticamente todos os workspaces e relatórios disponíveis
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class MultiReportSetup:
    def __init__(self):
        # Credenciais (use as mesmas que já funcionam)
        self.tenant_id = '00000000-0000-0000-0000-000000000004'
        self.client_id = '00000000-0000-0000-0000-000000000026'
        self.client_secret = 'REDACTED_SECRET'
        
        # URLs
        self.token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        self.powerbi_api = 'https://api.powerbi.com/v1.0/myorg'
        
        # Cache
        self.access_token = None
        self.token_expires = None
        
        # Dados descobertos
        self.workspaces = {}
        self.reports = {}
        self.datasets = {}
        
    def get_access_token(self):
        """Obtém access token"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        print("Obtendo access token...")
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)
            
            print("Token obtido com sucesso!")
            return self.access_token
            
        except Exception as e:
            print(f"Erro ao obter token: {e}")
            return None
    
    def get_headers(self):
        """Headers com autenticação"""
        token = self.get_access_token()
        if not token:
            raise Exception("Não foi possível obter token de acesso")
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def discover_workspaces(self):
        """Descobre todos os workspaces acessíveis"""
        print("\nDescobrindo workspaces...")
        
        try:
            url = f"{self.powerbi_api}/groups"
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            
            workspaces = response.json().get('value', [])
            
            print(f"Encontrados {len(workspaces)} workspaces:")
            
            for ws in workspaces:
                self.workspaces[ws['id']] = {
                    'id': ws['id'],
                    'name': ws['name'],
                    'type': ws.get('type', 'Unknown'),
                    'state': ws.get('state', 'Unknown')
                }
                
                print(f"   • {ws['name']} ({ws['id'][:8]}...)")
            
            return len(workspaces) > 0
            
        except Exception as e:
            print(f"Erro ao descobrir workspaces: {e}")
            return False
    
    def discover_reports_in_workspace(self, workspace_id, workspace_name):
        """Descobre relatórios em um workspace específico"""
        print(f"\nDescobrindo relatórios em '{workspace_name}'...")
        
        try:
            url = f"{self.powerbi_api}/groups/{workspace_id}/reports"
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            
            reports = response.json().get('value', [])
            
            workspace_reports = []
            
            for report in reports:
                report_data = {
                    'id': report['id'],
                    'name': report['name'],
                    'workspace_id': workspace_id,
                    'workspace_name': workspace_name,
                    'dataset_id': report.get('datasetId'),
                    'embed_url': report.get('embedUrl', ''),
                    'web_url': report.get('webUrl', ''),
                    'created_datetime': report.get('createdDateTime', ''),
                    'modified_datetime': report.get('modifiedDateTime', '')
                }
                
                self.reports[report['id']] = report_data
                workspace_reports.append(report_data)
                
                print(f"   {report['name']} ({report['id'][:8]}...)")
                if report.get('datasetId'):
                    print(f"      Dataset: {report['datasetId'][:8]}...")
            
            return workspace_reports
            
        except Exception as e:
            print(f"Erro ao descobrir relatórios em {workspace_name}: {e}")
            return []
    
    def discover_datasets_in_workspace(self, workspace_id, workspace_name):
        """Descobre datasets em um workspace específico"""
        print(f"\nDescobrindo datasets em '{workspace_name}'...")
        
        try:
            url = f"{self.powerbi_api}/groups/{workspace_id}/datasets"
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            
            datasets = response.json().get('value', [])
            
            for dataset in datasets:
                self.datasets[dataset['id']] = {
                    'id': dataset['id'],
                    'name': dataset['name'],
                    'workspace_id': workspace_id,
                    'workspace_name': workspace_name,
                    'configured_by': dataset.get('configuredBy', ''),
                    'is_refreshable': dataset.get('isRefreshable', False),
                    'is_effective_identity_required': dataset.get('isEffectiveIdentityRequired', False),
                    'is_effective_identity_roles_required': dataset.get('isEffectiveIdentityRolesRequired', False)
                }
                
                print(f"   {dataset['name']} ({dataset['id'][:8]}...)")
                
                # Informações importantes para RLS
                if dataset.get('isEffectiveIdentityRequired'):
                    print(f"      RLS obrigatório")
                if dataset.get('isEffectiveIdentityRolesRequired'):
                    print(f"      Roles RLS obrigatórios")
            
            return len(datasets)
            
        except Exception as e:
            print(f"Erro ao descobrir datasets em {workspace_name}: {e}")
            return 0
    
    def test_embed_token_generation(self, report_id, report_name):
        """Testa se é possível gerar embed token para um relatório"""
        print(f"\nTestando geração de token para '{report_name}'...")
        
        report = self.reports.get(report_id)
        if not report:
            print(f"Relatório não encontrado: {report_id}")
            return False
        
        try:
            url = f"{self.powerbi_api}/groups/{report['workspace_id']}/reports/{report_id}/GenerateToken"
            
            payload = {
                "accessLevel": "View",
                "allowSaveAs": False
            }
            
            response = requests.post(url, headers=self.get_headers(), json=payload, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"   Token gerado com sucesso! (expira: {token_data.get('expiration')})")
                return True
            else:
                error_detail = response.text
                print(f"   Erro ao gerar token: {response.status_code}")
                print(f"      Detalhes: {error_detail}")
                return False
                
        except Exception as e:
            print(f"   Erro ao testar token: {e}")
            return False
    
    def generate_config_files(self):
        """Gera arquivos de configuração baseados na descoberta"""
        print(f"\nGerando arquivos de configuração...")
        
        # 1. Gerar config para múltiplos relatórios
        reports_config = {}
        
        for report_id, report_data in self.reports.items():
            # Inferir categoria baseada no nome
            name_lower = report_data['name'].lower()
            if any(word in name_lower for word in ['vendas', 'sales', 'comercial']):
                category = 'vendas'
            elif any(word in name_lower for word in ['financeiro', 'finance', 'financial']):
                category = 'financeiro'
            elif any(word in name_lower for word in ['operacional', 'operations', 'ops']):
                category = 'operacional'
            elif any(word in name_lower for word in ['executivo', 'executive', 'dashboard']):
                category = 'executivo'
            elif any(word in name_lower for word in ['marketing', 'mkt']):
                category = 'marketing'
            elif any(word in name_lower for word in ['rh', 'hr', 'recursos']):
                category = 'rh'
            else:
                category = 'outros'
            
            reports_config[report_id] = {
                "name": report_data['name'],
                "workspace_id": report_data['workspace_id'],
                "dataset_id": report_data.get('dataset_id'),
                "description": f"Relatório {report_data['name']} do workspace {report_data['workspace_name']}",
                "category": category,
                "required_roles": ["admin", "viewer"],
                "required_regions": None,  # Todas as regiões
                "embed_url": report_data['embed_url'],
                "web_url": report_data['web_url'],
                "workspace_name": report_data['workspace_name']
            }
        
        # 2. Salvar em arquivo JSON
        config_file = Path('reports_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(reports_config, f, indent=4, ensure_ascii=False)
        
        print(f"   Arquivo criado: {config_file}")
        
        # 3. Gerar variável de ambiente
        env_var = json.dumps(reports_config, ensure_ascii=False)
        
        env_file = Path('.env.reports')
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"# Configuração de múltiplos relatórios\n")
            f.write(f"# Gerado automaticamente em {datetime.now()}\n\n")
            f.write(f"REPORTS_CONFIG='{env_var}'\n\n")
            f.write(f"# Relatórios encontrados:\n")
            for report_id, config in reports_config.items():
                f.write(f"# - {config['name']} (Categoria: {config['category']})\n")
        
        print(f"   Arquivo criado: {env_file}")
        
        # 4. Gerar exemplo de usuários
        users_example = {
            "admin": {
                "password": "REDACTED_SECRET",
                "roles": ["admin"],
                "region": "SP",
                "name": "Administrador",
                "reports": ["all"]
            },
            "usuario.vendas": {
                "password": "REDACTED_SECRET",
                "roles": ["sales", "viewer"],
                "region": "SP",
                "name": "Usuário Vendas",
                "reports": [report_id for report_id, config in reports_config.items() if config['category'] == 'vendas']
            },
            "usuario.financeiro": {
                "password": "REDACTED_SECRET",
                "roles": ["finance", "viewer"],
                "region": "SP",
                "name": "Usuário Financeiro",
                "reports": [report_id for report_id, config in reports_config.items() if config['category'] == 'financeiro']
            }
        }
        
        users_file = Path('users_example.json')
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users_example, f, indent=4, ensure_ascii=False)
        
        print(f"   Arquivo criado: {users_file}")
        
        return reports_config
    
    def run_full_discovery(self):
        """Executa descoberta completa"""
        print("POWER BI MULTI-REPORT SETUP")
        print("=" * 60)
        
        # 1. Descobrir workspaces
        if not self.discover_workspaces():
            print("Nenhum workspace encontrado. Verifique as permissões.")
            return False
        
        # 2. Descobrir relatórios e datasets em cada workspace
        total_reports = 0
        total_datasets = 0
        working_reports = 0
        
        for ws_id, ws_data in self.workspaces.items():
            # Relatórios
            reports = self.discover_reports_in_workspace(ws_id, ws_data['name'])
            total_reports += len(reports)
            
            # Datasets
            datasets_count = self.discover_datasets_in_workspace(ws_id, ws_data['name'])
            total_datasets += datasets_count
            
            # Testar alguns relatórios
            for report in reports[:3]:  # Testar até 3 por workspace
                if self.test_embed_token_generation(report['id'], report['name']):
                    working_reports += 1
        
        # 3. Gerar configurações
        if total_reports > 0:
            config = self.generate_config_files()
            
            # 4. Relatório final
            print("\n" + "=" * 60)
            print("DESCOBERTA CONCLUÍDA!")
            print("=" * 60)
            print(f"Workspaces encontrados: {len(self.workspaces)}")
            print(f"Relatórios encontrados: {total_reports}")
            print(f"Datasets encontrados: {total_datasets}")
            print(f"Relatórios testados: {working_reports}/{min(total_reports, len(self.workspaces) * 3)}")
            
            print(f"\nWorkspaces:")
            for ws_data in self.workspaces.values():
                reports_count = sum(1 for r in self.reports.values() if r['workspace_id'] == ws_data['id'])
                print(f"   • {ws_data['name']} ({reports_count} relatórios)")
            
            print(f"\nCategorias de relatórios:")
            categories = {}
            for report_data in config.values():
                cat = report_data['category']
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in categories.items():
                print(f"   • {cat.capitalize()}: {count} relatórios")
            
            print(f"\nArquivos gerados:")
            print(f"   • reports_config.json - Configuração completa")
            print(f"   • .env.reports - Variável de ambiente")
            print(f"   • users_example.json - Exemplo de usuários")
            
            print(f"\nPRÓXIMOS PASSOS:")
            print(f"1. Revise os arquivos gerados")
            print(f"2. Configure seus usuários em auth.py")
            print(f"3. Atualize config.py para usar a configuração")
            print(f"4. Teste com: python app.py")
            print(f"5. Deploy no Railway quando estiver funcionando")
            
            return True
        else:
            print("\nNenhum relatório encontrado!")
            return False

def main():
    print("POWER BI MULTI-REPORT DISCOVERY TOOL")
    print("Este script vai descobrir todos os workspaces e relatórios disponíveis")
    print("e criar a configuração automaticamente.")
    print()
    
    input("Pressione ENTER para continuar...")
    
    setup = MultiReportSetup()
    success = setup.run_full_discovery()
    
    if success:
        print("\nConfiguração gerada com sucesso!")
    else:
        print("\nFalha na configuração. Verifique os logs acima.")

if __name__ == "__main__":
    main()
