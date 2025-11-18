"""
Serviço de Backup e Recuperação do Banco de Dados
"""
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Configuração de backup
# Determinar caminho do diretório do backend (subir 2 níveis: app/services -> backend)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = os.environ.get("BACKUP_DIR", os.path.join(BACKEND_DIR, "backups"))
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))  # 30 dias por padrão
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BACKEND_DIR, "plans.db"))

# Criar diretório de backups se não existir
Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)


def create_backup(db_path: str = None) -> str:
    """
    Cria um backup do banco de dados SQLite
    
    Args:
        db_path: Caminho do banco de dados (padrão: DB_PATH)
    
    Returns:
        Caminho do arquivo de backup criado
    """
    if db_path is None:
        db_path = DB_PATH
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    # Gerar nome do backup com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"plans_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Criar conexão com o banco para garantir que está fechado
        conn = sqlite3.connect(db_path)
        conn.close()
        
        # Copiar arquivo do banco de dados
        shutil.copy2(db_path, backup_path)
        
        # Verificar integridade do backup
        verify_backup(backup_path)
        
        logger.info(f"Backup created successfully: {backup_path}")
        return backup_path
    
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        raise


def verify_backup(backup_path: str) -> bool:
    """
    Verifica a integridade de um backup
    
    Args:
        backup_path: Caminho do arquivo de backup
    
    Returns:
        True se o backup está íntegro
    """
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Verificar integridade do banco
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result[0] == "ok":
            logger.info(f"Backup integrity verified: {backup_path}")
            return True
        else:
            logger.error(f"Backup integrity check failed: {backup_path}")
            return False
    
    except Exception as e:
        logger.error(f"Error verifying backup: {str(e)}")
        return False


def restore_backup(backup_path: str, target_db_path: str = None) -> bool:
    """
    Restaura um backup do banco de dados
    
    Args:
        backup_path: Caminho do arquivo de backup
        target_db_path: Caminho de destino (padrão: DB_PATH)
    
    Returns:
        True se a restauração foi bem-sucedida
    """
    if target_db_path is None:
        target_db_path = DB_PATH
    
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    # Verificar integridade do backup antes de restaurar
    if not verify_backup(backup_path):
        raise ValueError(f"Backup file is corrupted: {backup_path}")
    
    try:
        # Criar backup do banco atual antes de restaurar (segurança)
        if os.path.exists(target_db_path):
            safety_backup = f"{target_db_path}.safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_db_path, safety_backup)
            logger.info(f"Safety backup created before restore: {safety_backup}")
        
        # Restaurar backup
        shutil.copy2(backup_path, target_db_path)
        
        # Verificar integridade do banco restaurado
        if verify_backup(target_db_path):
            logger.info(f"Backup restored successfully: {backup_path} -> {target_db_path}")
            return True
        else:
            logger.error(f"Restored database integrity check failed")
            return False
    
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        raise


def cleanup_old_backups(retention_days: int = None) -> int:
    """
    Remove backups antigos conforme política de retenção
    
    Args:
        retention_days: Número de dias para manter backups (padrão: RETENTION_DAYS)
    
    Returns:
        Número de backups removidos
    """
    if retention_days is None:
        retention_days = RETENTION_DAYS
    
    if not os.path.exists(BACKUP_DIR):
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    
    try:
        for filename in os.listdir(BACKUP_DIR):
            if not filename.startswith("plans_backup_") or not filename.endswith(".db"):
                continue
            
            file_path = os.path.join(BACKUP_DIR, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_time < cutoff_date:
                os.remove(file_path)
                removed_count += 1
                logger.info(f"Removed old backup: {filename}")
        
        logger.info(f"Cleanup completed: {removed_count} old backups removed")
        return removed_count
    
    except Exception as e:
        logger.error(f"Error during backup cleanup: {str(e)}")
        return removed_count


def list_backups() -> list:
    """
    Lista todos os backups disponíveis
    
    Returns:
        Lista de dicionários com informações dos backups
    """
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    
    try:
        for filename in os.listdir(BACKUP_DIR):
            if not filename.startswith("plans_backup_") or not filename.endswith(".db"):
                continue
            
            file_path = os.path.join(BACKUP_DIR, filename)
            file_size = os.path.getsize(file_path)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            backups.append({
                "filename": filename,
                "path": file_path,
                "size": file_size,
                "created_at": file_time.isoformat(),
                "age_days": (datetime.now() - file_time).days
            })
        
        # Ordenar por data (mais recente primeiro)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        return []


def get_backup_stats() -> dict:
    """
    Retorna estatísticas dos backups
    
    Returns:
        Dicionário com estatísticas
    """
    backups = list_backups()
    
    if not backups:
        return {
            "total_backups": 0,
            "total_size": 0,
            "oldest_backup": None,
            "newest_backup": None
        }
    
    total_size = sum(b["size"] for b in backups)
    
    return {
        "total_backups": len(backups),
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "oldest_backup": backups[-1]["created_at"] if backups else None,
        "newest_backup": backups[0]["created_at"] if backups else None,
        "retention_days": RETENTION_DAYS
    }

