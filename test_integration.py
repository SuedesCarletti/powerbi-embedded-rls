import requests
import json
from datetime import datetime, timedelta

class PowerBIDiscovery:
    def __init__(self):
        # Suas credenciais Service Principal (já funcionando!)
        self.tenant_id = '00000000-0000-0000-0000-000000000004'
        self.client_id = '00000000-0000-0000-0000-000000000026'
        self.client_secret = 'REDACTED_SECRET'
        
        # URLs
        self.token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        self.powerbi_api_url = 'https://api.powerbi.com/v1.0/myorg'
        
        # Cache do token
        self.access_token = None
        self.token_expires = None

    def get_access_token(self):
        """Obtém access token usando Service Principal"""
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
            response = requests.post(self.token_url, data=data)
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
        token = self.get_access_token()
        if not token:
            raise Exception("Não foi possível obter access token")
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def discover_resources(self):
        """Descobre workspaces, relatórios e datasets"""
        print("\n" + "="*60)
        print("DESCOBRINDO RECURSOS POWER BI")
        print("="*60)
        
        try:
            # Listar workspaces
            url = f"{self.powerbi_api_url}/groups"
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            workspaces = response.json().get('value', [])
            
            if not workspaces:
                print("Nenhum workspace encontrado.")
                print("Adicione o Service Principal como Admin/Member em um workspace.")
                return None
            
            print(f"\nEncontrados {len(workspaces)} workspaces:")
            for i, ws in enumerate(workspaces, 1):
                print(f"{i}. {ws['name']} (ID: {ws['id']})")
            
            # Selecionar workspace (usar primeiro por padrão)
            selected_workspace = workspaces[0]
            workspace_id = selected_workspace['id']
            workspace_name = selected_workspace['name']
            
            print(f"\nUsando workspace: {workspace_name}")
            
            # Listar relatórios do workspace
            url = f"{self.powerbi_api_url}/groups/{workspace_id}/reports"
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            
            reports = response.json().get('value', [])
            
            if not reports:
                print("Nenhum relatório encontrado neste workspace.")
                return None
            
            print(f"\nEncontrados {len(reports)} relatórios:")
            for i, report in enumerate(reports, 1):
                print(f"{i}. {report['name']} (ID: {report['id']})")
            
            # Usar primeiro relatório
            selected_report = reports[0]
            report_id = selected_report['id']
            report_name = selected_report['name']
            dataset_id = selected_report.get('datasetId')
            
            print(f"\nUsando relatório: {report_name}")
            
            # Testar geração de embed token
            print(f"\nTestando geração de embed token...")
            
            url = f"{self.powerbi_api_url}/groups/{workspace_id}/reports/{report_id}/GenerateToken"
            payload = {
                "accessLevel": "View",
                "allowSaveAs": False
            }
            
            response = requests.post(url, headers=self.get_headers(), json=payload)
            response.raise_for_status()
            
            embed_data = response.json()
            
            print("Embed token gerado com sucesso!")
            
            # Criar arquivo .env automático
            env_content = f"""# Service Principal (já configurado)
CLIENT_ID={self.client_id}
CLIENT_SECRET={self.client_secret}
TENANT_ID={self.tenant_id}

# Power BI Resources (descobertos automaticamente)
WORKSPACE_ID={workspace_id}
REPORT_ID={report_id}
DATASET_ID={dataset_id}

# Flask Configuration
SECRET_KEY=sua_chave_secreta_super_segura_{datetime.now().strftime('%Y%m%d')}
"""
            
            with open('.env', 'w') as f:
                f.write(env_content)
            
            print("\n" + "="*60)
            print("DESCOBERTA CONCLUÍDA COM SUCESSO!")
            print("="*60)
            print(f"Workspace: {workspace_name}")
            print(f"Relatório: {report_name}")
            print(f"Dataset ID: {dataset_id}")
            print(f"Arquivo .env criado automaticamente!")
            print("\nAgora você pode executar: python app.py")
            
            return {
                "workspace_id": workspace_id,
                "report_id": report_id,
                "dataset_id": dataset_id,
                "workspace_name": workspace_name,
                "report_name": report_name
            }
            
        except Exception as e:
            print(f"Erro na descoberta: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Detalhes: {e.response.text}")
            return None

def main():
    print("POWER BI EMBEDDED - DESCOBERTA DE RECURSOS")
    print("=" * 60)
    
    discovery = PowerBIDiscovery()
    result = discovery.discover_resources()
    
    if result:
        print("\nTudo pronto! Próximos passos:")
        print("1. Execute: python app.py")
        print("2. Acesse: http://localhost:5000")
        print("3. Login: admin / admin123")
        print("4. Deploy no Railway quando estiver funcionando!")
    else:
        print("\nAlgo deu errado. Verifique:")
        print("1. Se o Service Principal tem acesso ao workspace")
        print("2. Se há relatórios publicados no workspace")
        print("3. Se as credenciais estão corretas")

if __name__ == "__main__":
    main()
