import os
import requests
from datetime import datetime
import json

def check_environment():
    """Verifica se todas as variáveis de ambiente estão definidas"""
    print("=" * 60)
    print("VERIFICANDO VARIÁVEIS DE AMBIENTE")
    print("=" * 60)
    
    required_vars = [
        'CLIENT_ID',
        'CLIENT_SECRET', 
        'TENANT_ID',
        'WORKSPACE_ID',
        'REPORT_ID',
        'DATASET_ID',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    placeholder_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        
        if not value:
            missing_vars.append(var)
            print(f"{var}: NÃO DEFINIDA")
        elif value in ['SEU_WORKSPACE_ID_AQUI', 'SEU_REPORT_ID_AQUI', 'SEU_DATASET_ID_AQUI']:
            placeholder_vars.append(var)
            print(f"{var}: {value} (PLACEHOLDER)")
        else:
            # Mascarar valores sensíveis
            if 'SECRET' in var or 'ID' in var:
                display_value = value[:8] + "..." if len(value) > 8 else value
            else:
                display_value = value
            print(f"{var}: {display_value}")
    
    return missing_vars, placeholder_vars

def test_power_bi_connection():
    """Testa conexão com Power BI"""
    print("\n" + "=" * 60)
    print("TESTANDO CONEXÃO COM POWER BI")
    print("=" * 60)
    
    tenant_id = os.getenv('TENANT_ID')
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    
    if not all([tenant_id, client_id, client_secret]):
        print("Credenciais não encontradas!")
        return False
    
    try:
        # Teste de obtenção de token
        token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://analysis.windows.net/powerbi/api/.default'
        }
        
        print("Obtendo access token...")
        response = requests.post(token_url, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access_token']
            print("Token obtido com sucesso!")
            
            # Testar acesso ao workspace
            workspace_id = os.getenv('WORKSPACE_ID')
            if workspace_id and workspace_id != 'SEU_WORKSPACE_ID_AQUI':
                print(f"Testando acesso ao workspace: {workspace_id}")
                
                headers = {'Authorization': f'Bearer {access_token}'}
                ws_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}'
                
                ws_response = requests.get(ws_url, headers=headers, timeout=30)
                
                if ws_response.status_code == 200:
                    ws_info = ws_response.json()
                    print(f"Workspace encontrado: {ws_info.get('name', 'N/A')}")
                    
                    # Testar acesso ao relatório
                    report_id = os.getenv('REPORT_ID')
                    if report_id and report_id != 'SEU_REPORT_ID_AQUI':
                        print(f"Testando acesso ao relatório: {report_id}")
                        
                        report_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}'
                        report_response = requests.get(report_url, headers=headers, timeout=30)
                        
                        if report_response.status_code == 200:
                            report_info = report_response.json()
                            print(f"Relatório encontrado: {report_info.get('name', 'N/A')}")
                            
                            # Testar geração de embed token
                            print("Testando geração de embed token...")
                            
                            embed_url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}/GenerateToken'
                            embed_payload = {
                                "accessLevel": "View",
                                "allowSaveAs": False
                            }
                            
                            embed_response = requests.post(embed_url, headers=headers, json=embed_payload, timeout=30)
                            
                            if embed_response.status_code == 200:
                                print("Embed token gerado com sucesso!")
                                return True
                            else:
                                print(f"Erro ao gerar embed token: {embed_response.status_code}")
                                print(f"   Detalhes: {embed_response.text}")
                                return False
                        else:
                            print(f"Erro ao acessar relatório: {report_response.status_code}")
                            print(f"   Detalhes: {report_response.text}")
                            return False
                    else:
                        print("REPORT_ID não configurado ou é placeholder")
                        return False
                else:
                    print(f"Erro ao acessar workspace: {ws_response.status_code}")
                    print(f"   Detalhes: {ws_response.text}")
                    return False
            else:
                print("WORKSPACE_ID não configurado ou é placeholder")
                return False
                
        else:
            print(f"Erro ao obter token: {response.status_code}")
            print(f"   Detalhes: {response.text}")
            return False
            
    except Exception as e:
        print(f"Erro na conexão: {e}")
        return False

def main():
    print("RAILWAY POWER BI DEBUG")
    print(f"⏰ Timestamp: {datetime.now()}")
    print(f"Ambiente: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
    
    # Verificar variáveis de ambiente
    missing_vars, placeholder_vars = check_environment()
    
    # Testar conexão Power BI
    connection_ok = test_power_bi_connection()
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DO DIAGNÓSTICO")
    print("=" * 60)
    
    if missing_vars:
        print(f"Variáveis ausentes: {', '.join(missing_vars)}")
    
    if placeholder_vars:
        print(f"Variáveis com placeholder: {', '.join(placeholder_vars)}")
        print("Execute test_integration.py localmente para descobrir os valores corretos")
    
    if connection_ok:
        print("Conexão com Power BI: OK")
        print("Tudo configurado corretamente!")
    else:
        print("Conexão com Power BI: ERRO")
        
    print("\nPRÓXIMOS PASSOS:")
    if missing_vars or placeholder_vars:
        print("1. Configure as variáveis de ambiente no Railway")
        print("2. Execute test_integration.py localmente para descobrir IDs")
        print("3. Atualize as variáveis no Railway com os valores corretos")
    elif not connection_ok:
        print("1. Verifique se o Service Principal tem acesso ao workspace")
        print("2. Verifique se há relatórios no workspace")
        print("3. Verifique se as credenciais estão corretas")
    else:
        print("1. O problema pode ser na aplicação Flask")
        print("2. Verifique os logs detalhados da aplicação")
        print("3. Use as versões melhoradas dos arquivos fornecidos")

if __name__ == "__main__":
    main()
