#!/bin/bash
# Backup and restore utility for DEAN orchestration system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="${BACKUP_DIR:-$HOME/dean-backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Default configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-dean_orchestration}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Show usage
show_usage() {
    cat << EOF
DEAN Backup and Restore Utility

Usage: $0 [command] [options]

Commands:
  backup     Create a backup of DEAN system data
  restore    Restore from a backup
  list       List available backups
  verify     Verify backup integrity
  cleanup    Remove old backups

Options:
  -d, --dir <path>        Backup directory (default: $BACKUP_DIR)
  -n, --name <name>       Backup name (default: auto-generated)
  -f, --file <file>       Backup file for restore
  --postgres-only         Backup only PostgreSQL
  --redis-only           Backup only Redis
  --config-only          Backup only configuration
  --keep <days>          Keep backups for N days (cleanup command)
  -h, --help             Show this help message

Examples:
  $0 backup                          # Full backup
  $0 backup --postgres-only          # Database only
  $0 restore -f backup-20240101.tar  # Restore from file
  $0 list                           # Show all backups
  $0 cleanup --keep 30              # Remove backups older than 30 days
EOF
}

# Parse command line arguments
COMMAND=""
BACKUP_NAME=""
BACKUP_FILE=""
POSTGRES_ONLY=false
REDIS_ONLY=false
CONFIG_ONLY=false
KEEP_DAYS=30

while [[ $# -gt 0 ]]; do
    case $1 in
        backup|restore|list|verify|cleanup)
            COMMAND=$1
            shift
            ;;
        -d|--dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -n|--name)
            BACKUP_NAME="$2"
            shift 2
            ;;
        -f|--file)
            BACKUP_FILE="$2"
            shift 2
            ;;
        --postgres-only)
            POSTGRES_ONLY=true
            shift
            ;;
        --redis-only)
            REDIS_ONLY=true
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        --keep)
            KEEP_DAYS="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Validate command
if [ -z "$COMMAND" ]; then
    echo -e "${RED}No command specified${NC}"
    show_usage
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to check prerequisites
check_prerequisites() {
    local missing=()
    
    if [ "$POSTGRES_ONLY" != true ] && [ "$CONFIG_ONLY" != true ]; then
        command -v redis-cli >/dev/null 2>&1 || missing+=("redis-cli")
    fi
    
    if [ "$REDIS_ONLY" != true ] && [ "$CONFIG_ONLY" != true ]; then
        command -v pg_dump >/dev/null 2>&1 || missing+=("pg_dump")
        command -v psql >/dev/null 2>&1 || missing+=("psql")
    fi
    
    command -v tar >/dev/null 2>&1 || missing+=("tar")
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}Missing required tools: ${missing[*]}${NC}"
        echo "Please install missing tools before proceeding."
        exit 1
    fi
}

# Function to backup PostgreSQL
backup_postgres() {
    local backup_file="$1/postgres-backup.sql"
    
    echo -n "Backing up PostgreSQL database... "
    
    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -f "$backup_file" \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Function to backup Redis
backup_redis() {
    local backup_file="$1/redis-backup.rdb"
    
    echo -n "Backing up Redis data... "
    
    # Trigger Redis background save
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE >/dev/null 2>&1; then
        # Wait for background save to complete
        while [ "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" == "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" ]; do
            sleep 1
        done
        
        # Copy the dump file
        if [ -f "/var/lib/redis/dump.rdb" ]; then
            cp "/var/lib/redis/dump.rdb" "$backup_file"
        elif [ -f "$HOME/dump.rdb" ]; then
            cp "$HOME/dump.rdb" "$backup_file"
        else
            # Try to get from Redis config
            local dump_dir=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET dir | tail -1)
            local dump_file=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG GET dbfilename | tail -1)
            
            if [ -f "$dump_dir/$dump_file" ]; then
                cp "$dump_dir/$dump_file" "$backup_file"
            else
                echo -e "${YELLOW}⚠ Could not locate Redis dump file${NC}"
                return 1
            fi
        fi
        
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Function to backup configuration
backup_config() {
    local backup_dir="$1/config"
    
    echo -n "Backing up configuration files... "
    
    mkdir -p "$backup_dir"
    
    # Find project root
    local project_root="$SCRIPT_DIR/../.."
    
    # Copy configuration files
    if [ -d "$project_root/configs" ]; then
        cp -r "$project_root/configs" "$backup_dir/"
    fi
    
    if [ -f "$project_root/.env" ]; then
        cp "$project_root/.env" "$backup_dir/"
    fi
    
    # Copy docker-compose files if they exist
    for file in docker-compose.yml docker-compose.local.yml docker-compose.prod.yml; do
        if [ -f "$project_root/$file" ]; then
            cp "$project_root/$file" "$backup_dir/"
        fi
    done
    
    echo -e "${GREEN}✓${NC}"
    return 0
}

# Function to create backup
create_backup() {
    echo -e "${BLUE}Creating DEAN system backup...${NC}"
    
    # Generate backup name if not provided
    if [ -z "$BACKUP_NAME" ]; then
        BACKUP_NAME="dean-backup-$TIMESTAMP"
    fi
    
    local temp_dir="/tmp/$BACKUP_NAME"
    local backup_file="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
    
    # Check if backup already exists
    if [ -f "$backup_file" ]; then
        echo -e "${YELLOW}Backup already exists: $backup_file${NC}"
        read -p "Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
    
    # Create temporary directory
    mkdir -p "$temp_dir"
    
    # Create metadata file
    cat > "$temp_dir/metadata.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "version": "1.0",
    "components": {
        "postgres": $([[ "$REDIS_ONLY" == true || "$CONFIG_ONLY" == true ]] && echo "false" || echo "true"),
        "redis": $([[ "$POSTGRES_ONLY" == true || "$CONFIG_ONLY" == true ]] && echo "false" || echo "true"),
        "config": $([[ "$POSTGRES_ONLY" == true || "$REDIS_ONLY" == true ]] && echo "false" || echo "true")
    },
    "environment": {
        "postgres_host": "$POSTGRES_HOST",
        "postgres_port": "$POSTGRES_PORT",
        "postgres_db": "$POSTGRES_DB",
        "redis_host": "$REDIS_HOST",
        "redis_port": "$REDIS_PORT"
    }
}
EOF

    # Perform backups based on options
    local success=true
    
    if [ "$REDIS_ONLY" != true ] && [ "$CONFIG_ONLY" != true ]; then
        backup_postgres "$temp_dir" || success=false
    fi
    
    if [ "$POSTGRES_ONLY" != true ] && [ "$CONFIG_ONLY" != true ]; then
        backup_redis "$temp_dir" || success=false
    fi
    
    if [ "$POSTGRES_ONLY" != true ] && [ "$REDIS_ONLY" != true ]; then
        backup_config "$temp_dir" || success=false
    fi
    
    if [ "$success" = false ]; then
        echo -e "${RED}Backup failed!${NC}"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Create compressed archive
    echo -n "Creating backup archive... "
    if tar -czf "$backup_file" -C "/tmp" "$BACKUP_NAME"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Clean up temporary directory
    rm -rf "$temp_dir"
    
    # Show backup information
    local size=$(du -h "$backup_file" | cut -f1)
    echo ""
    echo -e "${GREEN}Backup completed successfully!${NC}"
    echo "Location: $backup_file"
    echo "Size: $size"
}

# Function to restore from backup
restore_backup() {
    echo -e "${BLUE}Restoring DEAN system from backup...${NC}"
    
    # Validate backup file
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${RED}No backup file specified${NC}"
        echo "Use -f option to specify backup file"
        exit 1
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
        exit 1
    fi
    
    # Extract to temporary directory
    local temp_dir="/tmp/dean-restore-$TIMESTAMP"
    mkdir -p "$temp_dir"
    
    echo -n "Extracting backup archive... "
    if tar -xzf "$BACKUP_FILE" -C "$temp_dir"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Find extracted directory
    local backup_dir=$(find "$temp_dir" -maxdepth 1 -type d | grep -v "^$temp_dir$" | head -1)
    
    # Read metadata
    if [ -f "$backup_dir/metadata.json" ]; then
        echo "Backup information:"
        jq . "$backup_dir/metadata.json"
    fi
    
    # Confirmation
    echo ""
    echo -e "${YELLOW}Warning: This will overwrite existing data!${NC}"
    read -p "Continue with restore? (yes/no) " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Restore cancelled"
        rm -rf "$temp_dir"
        exit 0
    fi
    
    # Restore components
    local success=true
    
    # Restore PostgreSQL
    if [ -f "$backup_dir/postgres-backup.sql" ]; then
        echo -n "Restoring PostgreSQL database... "
        if PGPASSWORD="$POSTGRES_PASSWORD" psql \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d postgres \
            -f "$backup_dir/postgres-backup.sql" >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            success=false
        fi
    fi
    
    # Restore Redis
    if [ -f "$backup_dir/redis-backup.rdb" ]; then
        echo -n "Restoring Redis data... "
        # This requires appropriate permissions and Redis restart
        echo -e "${YELLOW}⚠ Manual Redis restore required${NC}"
        echo "Copy $backup_dir/redis-backup.rdb to Redis data directory and restart Redis"
    fi
    
    # Restore configuration
    if [ -d "$backup_dir/config" ]; then
        echo -n "Restoring configuration files... "
        # Copy configuration files back
        local project_root="$SCRIPT_DIR/../.."
        
        if [ -d "$backup_dir/config/configs" ]; then
            cp -r "$backup_dir/config/configs" "$project_root/"
        fi
        
        echo -e "${GREEN}✓${NC}"
        echo -e "${YELLOW}Note: Review restored configuration files before use${NC}"
    fi
    
    # Clean up
    rm -rf "$temp_dir"
    
    if [ "$success" = true ]; then
        echo ""
        echo -e "${GREEN}Restore completed successfully!${NC}"
    else
        echo ""
        echo -e "${YELLOW}Restore completed with warnings${NC}"
    fi
}

# Function to list backups
list_backups() {
    echo -e "${BLUE}Available DEAN backups:${NC}"
    echo ""
    
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR"/*.tar.gz 2>/dev/null)" ]; then
        echo "No backups found in $BACKUP_DIR"
        return
    fi
    
    printf "%-40s %-10s %-20s\n" "Backup Name" "Size" "Date"
    echo "------------------------------------------------------------"
    
    for backup in "$BACKUP_DIR"/*.tar.gz; do
        local name=$(basename "$backup")
        local size=$(du -h "$backup" | cut -f1)
        local date=$(stat -c %y "$backup" 2>/dev/null || stat -f %Sm "$backup" 2>/dev/null)
        
        printf "%-40s %-10s %-20s\n" "$name" "$size" "${date:0:19}"
    done
}

# Function to verify backup
verify_backup() {
    echo -e "${BLUE}Verifying backup integrity...${NC}"
    
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${RED}No backup file specified${NC}"
        exit 1
    fi
    
    # Check if file exists
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
        exit 1
    fi
    
    # Test archive integrity
    echo -n "Testing archive integrity... "
    if tar -tzf "$BACKUP_FILE" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Archive is corrupted${NC}"
        exit 1
    fi
    
    # Extract and check contents
    local temp_dir="/tmp/dean-verify-$TIMESTAMP"
    mkdir -p "$temp_dir"
    
    tar -xzf "$BACKUP_FILE" -C "$temp_dir"
    local backup_dir=$(find "$temp_dir" -maxdepth 1 -type d | grep -v "^$temp_dir$" | head -1)
    
    # Check metadata
    if [ -f "$backup_dir/metadata.json" ]; then
        echo "Backup metadata:"
        jq . "$backup_dir/metadata.json"
    else
        echo -e "${YELLOW}⚠ No metadata found${NC}"
    fi
    
    # Check components
    echo ""
    echo "Components found:"
    [ -f "$backup_dir/postgres-backup.sql" ] && echo "✓ PostgreSQL backup"
    [ -f "$backup_dir/redis-backup.rdb" ] && echo "✓ Redis backup"
    [ -d "$backup_dir/config" ] && echo "✓ Configuration files"
    
    # Clean up
    rm -rf "$temp_dir"
    
    echo ""
    echo -e "${GREEN}Backup verification completed${NC}"
}

# Function to cleanup old backups
cleanup_backups() {
    echo -e "${BLUE}Cleaning up old backups...${NC}"
    echo "Keeping backups from the last $KEEP_DAYS days"
    
    local count=0
    
    find "$BACKUP_DIR" -name "*.tar.gz" -type f -mtime +$KEEP_DAYS | while read -r backup; do
        echo "Removing: $(basename "$backup")"
        rm -f "$backup"
        ((count++))
    done
    
    echo ""
    echo "Removed $count old backup(s)"
}

# Main execution
check_prerequisites

case "$COMMAND" in
    backup)
        create_backup
        ;;
    restore)
        restore_backup
        ;;
    list)
        list_backups
        ;;
    verify)
        verify_backup
        ;;
    cleanup)
        cleanup_backups
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_usage
        exit 1
        ;;
esac