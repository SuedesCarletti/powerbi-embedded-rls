#!/usr/bin/env python3
"""
Script para gerar configuração segura das variáveis de ambiente do Railway
SEM NUNCA expor credenciais no código!
"""

import json
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_secure_users_config():
    """
    Cria configuração de usuários segura
    VOCÊ DEVE INFORMAR AS SENHAS AQUI (não ficam no código final)
    """
    print("CONFIGURAÇÃO DE USUÁRIOS SEGURA")
    print("=" * 50)
    print("Este script vai gerar a configuração USERS_CONFIG para o Railway")
    print("As senhas serão convertidas em hash e NÃO aparecerão no código final.")
    print()
    
    # Coletar senhas de forma interativa (mais seguro)
    import getpass
    users = [
        ("admin", ["admin"], "Administrador", ["all"]),
        ("diretor.demo", ["director"], "Diretor Demo", ["gerencial", "margem"]),
        ("gestor.demo", ["manager", "sales"], "Gestor Demo", ["margem"]),
        ("analista.demo", ["analyst", "logistics"], "Analista Demo", ["margem"]),
    ]
    print("Informe as senhas para os usuários:")
    users_config = {}
    for login, roles, name, reports in users:
        users_config[login] = {
            "password": generate_password_hash(getpass.getpass(f"Senha do {login}: ")),
            "roles": roles,
            "region": "PR",
            "name": name,
            "reports": reports,
        }

    # Retorna o JSON compacto, ideal para variável de ambiente
    return json.dumps(users_config, separators=(',', ':'))
    
def generate_railway_config():
    """Gera todas as variáveis necessárias para o Railway"""
    
    print("\n" + "=" * 60)
    print("CONFIGURAÇÃO DO RAILWAY - POWER BI EMBEDDED")
    print("=" * 60)
    print()
    
    # Informações que o usuário precisa fornecer
    print("VOCÊ PRECISA FORNECER ESTAS INFORMAÇÕES:")
    print("1. Credenciais do Service Principal (Azure)")
    print("2. IDs do Power BI (Workspace, Report, Dataset)")
    print("3. Senhas dos usuários do sistema")
    print()
    
    print("CREDENCIAIS DO SERVICE PRINCIPAL:")
    print("(Obtidas no Azure Portal > App registrations)")
    
    client_id = input("CLIENT_ID (Application ID): ").strip()
    if not client_id:
        print("CLIENT_ID é obrigatório!")
        return None
        
    client_secret = input("CLIENT_SECRET: ").strip()
    if not client_secret:
        print("CLIENT_SECRET é obrigatório!")
        return None
        
    tenant_id = input("TENANT_ID: ").strip()
    if not tenant_id:
        print("TENANT_ID é obrigatório!")
        return None
    
    print("\nIDs DO POWER BI:")
    print("(Obtidos executando test_integration.py ou diagnose_powerbi.py)")
    
    workspace_id = input("WORKSPACE_ID: ").strip()
    if not workspace_id:
        print("WORKSPACE_ID é obrigatório!")
        return None
        
    report_id = input("REPORT_ID: ").strip()
    if not report_id:
        print("REPORT_ID é obrigatório!")
        return None
        
    dataset_id = input("DATASET_ID (opcional, deixe vazio se não usar RLS): ").strip()
    
    print("\nCONFIGURAÇÃO DE USUÁRIOS:")
    users_json = create_secure_users_config()
    
    print("\nOUTRAS CONFIGURAÇÕES:")
    secret_key = input("SECRET_KEY (deixe vazio para gerar automaticamente): ").strip()
    if not secret_key:
        # Gerar chave segura automaticamente
        import secrets
        secret_key = secrets.token_urlsafe(32)
        print(f"SECRET_KEY gerada automaticamente")
    
    # Montar todas as variáveis
    variables = {
        "CLIENT_ID": client_id,
        "CLIENT_SECRET": client_secret,
        "TENANT_ID": tenant_id,
        "WORKSPACE_ID": workspace_id,
        "REPORT_ID": report_id,
        "SECRET_KEY": secret_key,
        "USERS_CONFIG": users_json,
        "FLASK_ENV": "production",
        "LOG_LEVEL": "INFO"
    }
    
    # Adicionar DATASET_ID apenas se fornecido
    if dataset_id:
        variables["DATASET_ID"] = dataset_id
    
    return variables

def save_variables_to_file(variables):
    """Salva variáveis em arquivo .env e instruções para Railway"""
    
    # Criar arquivo .env para desenvolvimento local
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(f"# Configuração Power BI Embedded\n")
        f.write(f"# Gerado em: {datetime.now()}\n")
        f.write(f"# IMPORTANTE: Este arquivo contém informações sensíveis!\n\n")
        
        for key, value in variables.items():
            f.write(f"{key}={value}\n")
    
    print("Arquivo .env criado para desenvolvimento local")
    
    # Criar arquivo com instruções para Railway
    with open('railway_setup.md', 'w', encoding='utf-8') as f:
        f.write("# Configuração das Variáveis de Ambiente no Railway\n\n")
        f.write("## Acesse o painel do Railway:\n")
        f.write("1. Va para o seu projeto no Railway\n")
        f.write("2. Clique na aba 'Variables'\n")
        f.write("3. Adicione cada variável abaixo:\n\n")
        
        f.write("## Variáveis a configurar:\n\n")
        
        for key, value in variables.items():
            # Mascarar valores sensíveis nas instruções
            if key in ['CLIENT_SECRET', 'SECRET_KEY']:
                display_value = "***VALOR_SENSIVEL***"
            elif key == 'USERS_CONFIG':
                display_value = "***JSON_COM_USUARIOS***"
            else:
                display_value = value[:20] + "..." if len(str(value)) > 20 else value
                
            f.write(f"### {key}\n")
            f.write(f"```\n{display_value}\n```\n\n")
        
        f.write("## Valores reais (COPIE E COLE NO RAILWAY):\n\n")
        f.write("**ATENÇÃO: Mantenha estas informações seguras!**\n\n")
        
        for key, value in variables.items():
            f.write(f"**{key}:**\n")
            f.write("```\n")
            f.write(str(value))
            f.write("\n```\n\n")
    
    print("Arquivo railway_setup.md criado com instruções")

def main():
    print("SETUP SEGURO DAS VARIÁVEIS DO RAILWAY")
    print("Este script NÃO salva credenciais no código!")
    print("Todas as informações sensíveis ficam apenas nas variáveis de ambiente.")
    print()
    
    try:
        # Gerar configuração
        variables = generate_railway_config()
        
        if not variables:
            print("Configuração cancelada ou incompleta")
            return
        
        # Salvar arquivos
        save_variables_to_file(variables)
        
        print("\n" + "=" * 60)
        print("CONFIGURAÇÃO CONCLUÍDA!")
        print("=" * 60)
        
        print("\nArquivos gerados:")
        print("• .env - Para desenvolvimento local")
        print("• railway_setup.md - Instruções para Railway")
        
        print("\nPRÓXIMOS PASSOS:")
        print("1. Abra railway_setup.md")
        print("2. Copie as variáveis para o Railway")
        print("3. Faça deploy da aplicação")
        print("4. Teste o login com os usuários configurados")
        
        print("\nUSUÁRIOS CONFIGURADOS:")
        print("• admin - Acesso administrativo total")
        print("• viewer - Visualização básica")
        print("• usuario.sp - Usuário região SP")
        print("• usuario.rj - Usuário região RJ")
        
        print("\nLEMBRETE DE SEGURANÇA:")
        print("• Nunca commite o arquivo .env")
        print("• Mantenha railway_setup.md seguro")
        print("• Delete railway_setup.md após configurar")
        print("• Mude as senhas regularmente")
        
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário")
    except Exception as e:
        print(f"\nErro durante configuração: {e}")

if __name__ == "__main__":
    main()
