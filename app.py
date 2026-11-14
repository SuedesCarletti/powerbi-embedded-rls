from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from powerbi_service import PowerBIService
from auth import login_required, authenticate_user, get_user_identity, user_can_access_report, admin_required, get_current_user
from config import Config
import json
import os
import logging
import traceback
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # true quando o app estiver atrás de HTTPS (cookie Secure não persiste em HTTP puro)
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
)
app.config.from_object(Config)

# Inicializar PowerBIService
try:
    powerbi = PowerBIService()
    logger.info("PowerBIService inicializado com sucesso!")
    
    # Validar configuração
    issues = Config.validate_config()
    if issues:
        # Usamos logger.warning para avisos, não erros fatais
        for issue in issues:
            logger.warning(f"Problema de configuração: {issue}")
    else:
        logger.info("Configuração validada com sucesso!")
    
    # Log do sistema de relatórios detectado
    env_info = Config.list_env_reports()
    logger.info(f"Sistema de relatórios: {env_info['system_type']} com {env_info['reports_found']} relatórios")
        
except Exception as e:
    logger.error(f"Erro fatal ao inicializar PowerBIService: {e}")
    # Em caso de erro na inicialização, a aplicação não deve continuar
    powerbi = None
    
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            session['user'] = user
            session.permanent = True
            logger.info(f"Usuário logado: {username} (Região: {user.get('region')})")
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Tentativa de login falhada para: {username}")
            flash('Credenciais inválidas!', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    
    # Obter relatórios acessíveis para o usuário
    user_reports = Config.get_reports_for_user(
        user.get('roles', []), 
        user.get('region')
    )
    
    # Agrupar por categoria
    reports_by_category = {}
    for report_name, config in user_reports.items():
        category = config.get('category', 'outros')
        if category not in reports_by_category:
            reports_by_category[category] = []
        
        # Usar nome do relatório como ID para as rotas
        reports_by_category[category].append({
            'id': report_name,  # Nome do relatório (ex: 'executivo', 'vendas')
            'name': config['name'],  # Nome para exibição
            'description': config.get('description', ''),
            'category': category
        })
    
    logger.info(f"Dashboard acessado por: {user['username']} - {len(user_reports)} relatórios disponíveis")
    
    return render_template('dashboard.html', 
                         user=user, 
                         reports_by_category=reports_by_category)

@app.route('/embed/<report_name>')
@login_required
def embed(report_name):
    """Página de embed que usa o nome amigável do relatório."""
    user = get_current_user()
    
    # Verificar se o usuário pode acessar este relatório
    if not user_can_access_report(report_name):
        logger.warning(f"Acesso negado ao relatório '{report_name}' para o usuário {user['username']}")
        flash('Você não tem permissão para acessar este relatório.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Obter configuração do relatório pelo nome
    report_config = Config.get_report_by_name(report_name)
    if not report_config:
        logger.error(f"Relatório '{report_name}' não encontrado na configuração")
        flash('O relatório solicitado não foi encontrado.', 'danger')
        return redirect(url_for('dashboard'))
    
    logger.info(f"Embed do relatório '{report_config['name']}' ({report_name}) acessado por {user['username']}")

    # CORREÇÃO: Usar cor corporativa padrão #002951
    background_color = report_config.get('background_color')
    
    if not background_color:
        # Usar cor corporativa como padrão
        background_color = Config.CORPORATE_PRIMARY_COLOR  # #002951
        logger.info(f"Usando cor corporativa padrão: {background_color}")
    else:
        logger.info(f"Cor de fundo definida na configuração: {background_color}")
    
    # Determinar cor do texto baseada no fundo
    text_color = report_config.get('text_color')
    if not text_color:
        # Se o fundo for escuro (como #002951), usar texto claro
        if background_color in [Config.CORPORATE_PRIMARY_COLOR, '#002951', '#001a2e', '#1a1a1a']:
            text_color = '#ffffff'
        else:
            text_color = '#333333'
    
    # Obter paleta de cores corporativas para uso no template
    corporate_colors = Config.get_corporate_colors()
    
    logger.info(f"Cores aplicadas - Fundo: {background_color}, Texto: {text_color}")

    return render_template(
        'embed.html', 
        user=user,
        report_name_param=report_name,
        report_name=report_config['name'],
        background_color=background_color,
        text_color=text_color,
        corporate_colors=corporate_colors
    )

@app.route('/api/embed-config')
@app.route('/api/embed-config/<report_name>')
@login_required
def api_embed_config(report_name=None):
    """API para fornecer configuração de embed."""
    logger.info(f"Iniciando configuração de embed para o relatório '{report_name or 'padrão'}'...")
    
    try:
        if powerbi is None:
            raise ValueError("Serviço do Power BI não inicializado.")

        user = get_current_user()
        
        # Se não foi especificado um relatório, usar o primeiro disponível para o usuário
        if not report_name:
            user_reports = Config.get_reports_for_user(user.get('roles', []), user.get('region'))
            if not user_reports:
                raise PermissionError("Usuário não tem acesso a nenhum relatório")
            
            report_name = list(user_reports.keys())[0]
            logger.info(f"Usando relatório padrão: {report_name}")
        
        # Validação de permissão
        if not user_can_access_report(report_name):
            raise PermissionError(f"Acesso negado ao relatório '{report_name}'")

        # Obter configuração do relatório
        report_config = Config.get_report_by_name(report_name)
        if not report_config:
            raise FileNotFoundError(f"Relatório '{report_name}' não encontrado.")

        logger.info(f"Gerando embed para usuário: {user['username']} (Região: {user.get('region')})")
        logger.info(f"Relatório: {report_config['name']} (Workspace: {report_config['workspace_id'][:8]}..., Report: {report_config['report_id'][:8]}...)")

        # Obter identidade do usuário para RLS (se habilitado)
        user_identity = get_user_identity() if Config.ENABLE_RLS else None
        if user_identity:
            logger.info(f"Identidade RLS: {user_identity}")

        # Gerar configuração de embed usando o novo método
        embed_config = powerbi.get_embed_config_for_report_name(report_name, user_identity)
        
        logger.info(f"Configuração de embed para '{report_name}' gerada com sucesso!")
        return jsonify(embed_config)

    except FileNotFoundError as e:
        logger.error(f"{e}")
        return jsonify({"error": str(e)}), 404
    except PermissionError as e:
        logger.warning(f"{e}")
        return jsonify({"error": "Acesso negado"}), 403
    except Exception as e:
        error_msg = f"Erro interno ao gerar configuração de embed: {str(e)}"
        logger.error(f"{error_msg}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({"error": "Não foi possível carregar o relatório. Contacte o administrador."}), 500

@app.route('/api/reports')
@login_required
def api_reports():
    """API para listar relatórios disponíveis para o usuário"""
    user = session['user']
    
    user_reports = Config.get_reports_for_user(
        user.get('roles', []), 
        user.get('region')
    )
    
    # Formatar para API
    formatted_reports = []
    for report_name, config in user_reports.items():
        formatted_reports.append({
            'id': report_name,  # Nome do relatório
            'name': config['name'],  # Nome para exibição
            'description': config.get('description', ''),
            'category': config.get('category', 'outros'),
            'embed_url': url_for('embed', report_name=report_name),
            'workspace_id': config['workspace_id'],
            'report_id': config['report_id']
        })
    
    return jsonify({
        'user': {
            'username': user['username'],
            'region': user['region'],
            'roles': user.get('roles', [])
        },
        'reports': formatted_reports,
        'total': len(formatted_reports),
        'system_info': Config.list_env_reports()
    })

@app.route('/admin/reports')
@admin_required
def admin_reports():
    """Painel administrativo para gerenciar relatórios"""
    all_reports = Config.get_reports_config()
    categories = Config.get_categories()
    
    return render_template('reports.html',
                         reports=all_reports,
                         categories=categories)

@app.route('/api/admin/reports')
@admin_required
def api_admin_reports():
    """API administrativa para listar todos os relatórios"""
    all_reports = Config.get_reports_config()
    
    # Adicionar informações extras para admin
    enriched_reports = {}
    for report_name, config in all_reports.items():
        enriched_config = config.copy()
        
        # Adicionar informações do sistema
        enriched_config['system_name'] = report_name
        enriched_config['env_vars'] = {
            'report_id_var': f"REPORT_ID_{report_name.upper()}",
            'dataset_id_var': f"DATASET_ID_{report_name.upper()}",
            'workspace_id_var': f"WORKSPACE_ID_{report_name.upper()}",
            'metadata_var': f"METADATA_{report_name.upper()}"
        }
        
        enriched_reports[report_name] = enriched_config
    
    return jsonify({
        'reports': enriched_reports,
        'total': len(enriched_reports),
        'categories': Config.get_categories(),
        'system_info': Config.list_env_reports(),
        'config_issues': Config.validate_config()
    })

@app.route('/api/health')
def health_check():
    """Endpoint para verificar saúde da aplicação"""
    try:
        status = {
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "powerbi_service": powerbi is not None,
            "config_loaded": app.config.get('SECRET_KEY') is not None,
        }
        
        # Informações sobre relatórios
        reports = Config.get_reports_config()
        status["reports_configured"] = len(reports)
        status["reports_system"] = Config.list_env_reports()["system_type"]
        
        # Testar conexão com Power BI se possível
        if powerbi:
            try:
                connection_test = powerbi.test_connection()
                status["powerbi_connection"] = connection_test
            except Exception as e:
                status["powerbi_connection"] = {"status": "error", "message": str(e)}
        
        # Informações de configuração (sem dados sensíveis)
        config_issues = Config.validate_config()
        status["config_issues"] = len(config_issues)
        
        # Para admins, mostrar detalhes dos problemas
        if 'admin' in session.get('user', {}).get('roles', []):
            status["config_details"] = config_issues
            status["system_info"] = powerbi.get_system_info() if powerbi else None
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": str(datetime.now())
        }), 500

@app.route('/api/test-report/<report_name>')
@admin_required
def api_test_report(report_name):
    """API para testar um relatório específico (apenas admin)"""
    try:
        if powerbi is None:
            return jsonify({"status": "error", "message": "PowerBI service não inicializado"}), 500
        
        # Verificar se o relatório existe
        report_config = Config.get_report_by_name(report_name)
        if not report_config:
            return jsonify({"status": "error", "message": f"Relatório '{report_name}' não encontrado"}), 404
        
        # Testar obtenção de informações do relatório
        report_info = powerbi.get_report_info_by_id(
            report_config['workspace_id'], 
            report_config['report_id']
        )
        
        # Testar geração de embed token
        embed_data = powerbi.get_embed_token_for_report(
            report_config['workspace_id'],
            report_config['report_id'],
            report_config.get('dataset_id')
        )
        
        return jsonify({
            "status": "success",
            "message": f"Relatório '{report_name}' testado com sucesso",
            "report_info": {
                "name": report_info.get('name'),
                "id": report_info.get('id'),
                "embedUrl": report_info.get('embedUrl'),
                "datasetId": report_info.get('datasetId')
            },
            "token_info": {
                "tokenId": embed_data.get('tokenId'),
                "expiration": embed_data.get('expiration')
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar relatório '{report_name}': {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/logout')
def logout():
    user = session.get('user', {}).get('username', 'desconhecido')
    session.clear()
    flash('Sessão terminada com sucesso.', 'info')
    logger.info(f"Usuário deslogado: {user}")
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro 500: {str(error)}")
    return render_template('error.html', error="Erro interno do servidor"), 500

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"Página não encontrada: {request.url}")
    return render_template('error.html', error="Página não encontrada"), 404

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"Acesso negado: {request.url}")
    return render_template('error.html', error="Acesso negado"), 403

# Session configuration
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = Config.SESSION_TIMEOUT

# Rota para debug/desenvolvimento
@app.route('/debug/config')
@admin_required
def debug_config():
    """Página de debug para administradores (apenas em desenvolvimento)"""
    if Config.is_production():
        return jsonify({"error": "Debug não disponível em produção"}), 403
    
    return jsonify({
        "masked_config": Config.get_masked_config(),
        "reports_info": Config.list_env_reports(),
        "validation_issues": Config.validate_config(),
        "system_info": powerbi.get_system_info() if powerbi else None
    })

# NOVA ROTA: API para definir cor corporativa padrão
@app.route('/api/admin/set-corporate-color', methods=['POST'])
@admin_required
def api_set_corporate_color():
    """API para definir nova cor corporativa padrão (apenas admin)"""
    try:
        data = request.get_json()
        new_color = data.get('color', Config.CORPORATE_PRIMARY_COLOR)
        
        # Validar formato hex da cor
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', new_color):
            return jsonify({"error": "Formato de cor inválido. Use formato hex (#RRGGBB)"}), 400
        
        # Em um sistema real, salvaria no banco de dados
        # Por enquanto, apenas informativo
        
        logger.info(f"Admin {session['user']['username']} definiu nova cor corporativa: {new_color}")
        
        return jsonify({
            "status": "success",
            "message": f"Cor corporativa atualizada para {new_color}",
            "current_color": new_color,
            "instruction": f"Para tornar permanente, atualize CORPORATE_PRIMARY_COLOR no config.py para '{new_color}'",
            "preview_colors": {
                "primary": new_color,
                "primary_light": adjust_color_brightness(new_color, 0.2),
                "primary_dark": adjust_color_brightness(new_color, -0.2)
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao definir cor corporativa: {e}")
        return jsonify({"error": str(e)}), 500

def adjust_color_brightness(hex_color, factor):
    """Ajusta o brilho de uma cor hex"""
    try:
        # Remove # se presente
        hex_color = hex_color.lstrip('#')
        
        # Converte para RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Ajusta brilho
        r = max(0, min(255, int(r * (1 + factor))))
        g = max(0, min(255, int(g * (1 + factor))))
        b = max(0, min(255, int(b * (1 + factor))))
        
        # Converte de volta para hex
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return hex_color  # Retorna original se erro

if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask...")
    logger.info(f"Modo: {'Debug' if app.debug else 'Produção'}")
    
    # Log do sistema de relatórios
    reports = Config.get_reports_config()
    env_info = Config.list_env_reports()
    logger.info(f"Sistema de relatórios: {env_info['system_type']}")
    logger.info(f"Relatórios configurados: {len(reports)}")
    
    for name, config in reports.items():
        logger.info(f"   • {name}: {config['name']} ({config.get('category', 'N/A')})")
    
    app.run(debug=os.getenv('FLASK_DEBUG') == '1')
