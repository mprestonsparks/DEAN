#!/bin/bash

# DEAN Hardware Optimization Script
# Detects system specifications and applies hardware-specific optimizations

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEAN_ROOT="$(dirname "$SCRIPT_DIR")"
HARDWARE_CONFIG_DIR="$DEAN_ROOT/configs/hardware"

echo -e "${BLUE}DEAN Hardware Optimization Script${NC}"
echo "=================================="
echo ""

# Function to detect CPU information
detect_cpu() {
    echo -e "${YELLOW}Detecting CPU...${NC}"
    
    if [ -f /proc/cpuinfo ]; then
        CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
        CPU_CORES=$(grep -c "processor" /proc/cpuinfo)
        CPU_THREADS=$(grep -c "processor" /proc/cpuinfo)
        
        # Check for Intel i7
        if [[ "$CPU_MODEL" == *"i7"* ]]; then
            echo -e "${GREEN}✓ Intel i7 detected: $CPU_MODEL${NC}"
            echo "  Cores: $CPU_CORES"
            DETECTED_CPU="i7"
        else
            echo -e "${YELLOW}⚠ CPU: $CPU_MODEL${NC}"
            echo "  Cores: $CPU_CORES"
            DETECTED_CPU="generic"
        fi
    else
        echo -e "${RED}✗ Unable to detect CPU information${NC}"
        DETECTED_CPU="unknown"
    fi
}

# Function to detect memory
detect_memory() {
    echo -e "${YELLOW}Detecting Memory...${NC}"
    
    TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
    
    echo -e "${GREEN}✓ Total RAM: ${TOTAL_MEM_GB}GB${NC}"
    
    if [ $TOTAL_MEM_GB -ge 32 ]; then
        echo "  Sufficient memory for high-performance configuration"
        MEMORY_PROFILE="high"
    elif [ $TOTAL_MEM_GB -ge 16 ]; then
        echo "  Sufficient memory for standard configuration"
        MEMORY_PROFILE="standard"
    else
        echo -e "${YELLOW}⚠ Limited memory detected. Performance may be impacted${NC}"
        MEMORY_PROFILE="low"
    fi
}

# Function to detect NVIDIA GPU
detect_gpu() {
    echo -e "${YELLOW}Detecting GPU...${NC}"
    
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
        GPU_NAME=$(echo $GPU_INFO | cut -d, -f1 | xargs)
        GPU_MEMORY=$(echo $GPU_INFO | cut -d, -f2 | xargs)
        
        if [[ "$GPU_NAME" == *"RTX 3080"* ]]; then
            echo -e "${GREEN}✓ NVIDIA RTX 3080 detected${NC}"
            echo "  Memory: ${GPU_MEMORY}MB"
            DETECTED_GPU="rtx3080"
            GPU_AVAILABLE=true
        else
            echo -e "${YELLOW}⚠ NVIDIA GPU detected: $GPU_NAME${NC}"
            echo "  Memory: ${GPU_MEMORY}MB"
            DETECTED_GPU="nvidia_other"
            GPU_AVAILABLE=true
        fi
        
        # Check CUDA
        if command -v nvcc &> /dev/null; then
            CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $6}' | cut -d, -f1)
            echo -e "${GREEN}✓ CUDA $CUDA_VERSION detected${NC}"
        else
            echo -e "${YELLOW}⚠ CUDA not found. GPU acceleration may be limited${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No NVIDIA GPU detected${NC}"
        DETECTED_GPU="none"
        GPU_AVAILABLE=false
    fi
}

# Function to detect storage
detect_storage() {
    echo -e "${YELLOW}Detecting Storage...${NC}"
    
    # Check if NVMe
    if [ -d /sys/class/nvme ]; then
        echo -e "${GREEN}✓ NVMe SSD detected${NC}"
        STORAGE_TYPE="nvme"
    elif [ -d /sys/class/scsi_disk ]; then
        # Check if SSD
        for disk in /sys/block/sd*; do
            if [ -f "$disk/queue/rotational" ]; then
                ROTATIONAL=$(cat "$disk/queue/rotational")
                if [ "$ROTATIONAL" -eq 0 ]; then
                    echo -e "${GREEN}✓ SSD detected${NC}"
                    STORAGE_TYPE="ssd"
                    break
                fi
            fi
        done
        
        if [ -z "$STORAGE_TYPE" ]; then
            echo -e "${YELLOW}⚠ HDD detected. Performance may be impacted${NC}"
            STORAGE_TYPE="hdd"
        fi
    else
        echo "Storage type: Unknown"
        STORAGE_TYPE="unknown"
    fi
}

# Function to apply CPU optimizations
apply_cpu_optimizations() {
    echo -e "${YELLOW}Applying CPU optimizations...${NC}"
    
    # Set CPU governor to performance (requires root)
    if [ "$EUID" -eq 0 ]; then
        for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
            echo "performance" > "$cpu" 2>/dev/null || true
        done
        echo -e "${GREEN}✓ CPU governor set to performance${NC}"
    else
        echo -e "${YELLOW}⚠ Run as root to set CPU governor${NC}"
    fi
    
    # Set process nice values in docker-compose
    if [ "$DETECTED_CPU" == "i7" ] && [ $CPU_CORES -ge 8 ]; then
        echo -e "${GREEN}✓ Using i7 8-core optimizations${NC}"
        SELECTED_CONFIG="i7_rtx3080.yaml"
    else
        echo "Using generic CPU configuration"
        SELECTED_CONFIG="generic.yaml"
    fi
}

# Function to apply memory optimizations
apply_memory_optimizations() {
    echo -e "${YELLOW}Applying memory optimizations...${NC}"
    
    # Configure swappiness (requires root)
    if [ "$EUID" -eq 0 ]; then
        echo 10 > /proc/sys/vm/swappiness
        echo -e "${GREEN}✓ Swappiness set to 10${NC}"
        
        # Disable transparent huge pages
        echo never > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true
        echo never > /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null || true
        echo -e "${GREEN}✓ Transparent huge pages disabled${NC}"
    else
        echo -e "${YELLOW}⚠ Run as root to apply memory optimizations${NC}"
    fi
}

# Function to apply GPU optimizations
apply_gpu_optimizations() {
    if [ "$GPU_AVAILABLE" = true ]; then
        echo -e "${YELLOW}Applying GPU optimizations...${NC}"
        
        # Enable persistence mode (requires root)
        if [ "$EUID" -eq 0 ]; then
            nvidia-smi -pm 1
            echo -e "${GREEN}✓ GPU persistence mode enabled${NC}"
            
            # Set power limit for RTX 3080
            if [ "$DETECTED_GPU" == "rtx3080" ]; then
                nvidia-smi -pl 320
                echo -e "${GREEN}✓ GPU power limit set to 320W${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ Run as root to apply GPU optimizations${NC}"
        fi
        
        # Check Docker nvidia runtime
        if docker info 2>/dev/null | grep -q nvidia; then
            echo -e "${GREEN}✓ Docker nvidia runtime available${NC}"
        else
            echo -e "${RED}✗ Docker nvidia runtime not found${NC}"
            echo "  Install nvidia-container-runtime for GPU support"
        fi
    fi
}

# Function to create optimized docker-compose override
create_docker_override() {
    echo -e "${YELLOW}Creating Docker Compose override...${NC}"
    
    # Select appropriate configuration
    if [ "$DETECTED_CPU" == "i7" ] && [ "$DETECTED_GPU" == "rtx3080" ] && [ "$MEMORY_PROFILE" == "high" ]; then
        CONFIG_FILE="$HARDWARE_CONFIG_DIR/i7_rtx3080.yaml"
        echo -e "${GREEN}✓ Using i7/RTX3080 optimized configuration${NC}"
    else
        CONFIG_FILE="$HARDWARE_CONFIG_DIR/generic.yaml"
        echo -e "${YELLOW}⚠ Using generic configuration${NC}"
        echo "  For best performance, use i7 CPU + RTX 3080 GPU + 32GB RAM"
    fi
    
    # Create docker-compose.hardware.yml
    cat > "$DEAN_ROOT/docker-compose.hardware.yml" << EOF
# Hardware-optimized Docker Compose override
# Generated by optimize_for_hardware.sh
# Hardware: CPU=$DETECTED_CPU, GPU=$DETECTED_GPU, Memory=$MEMORY_PROFILE

version: '3.8'

services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 2G
    environment:
      - OMP_NUM_THREADS=4
      - PYTHONOPTIMIZE=2

  evolution-api:
    deploy:
      resources:
        limits:
          cpus: '6.0'
          memory: 12G
        reservations:
          cpus: '2.0'
          memory: 4G
EOF

    # Add GPU configuration if available
    if [ "$GPU_AVAILABLE" = true ]; then
        cat >> "$DEAN_ROOT/docker-compose.hardware.yml" << EOF
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
      - CUDA_VISIBLE_DEVICES=0
      - TF_FORCE_GPU_ALLOW_GROWTH=true
      - OMP_NUM_THREADS=6
      - PYTHONOPTIMIZE=2
EOF
    fi

    cat >> "$DEAN_ROOT/docker-compose.hardware.yml" << EOF

  indexagent:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  postgres-prod:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    command: |
      postgres
      -c shared_buffers=1GB
      -c effective_cache_size=3GB
      -c maintenance_work_mem=256MB
      -c work_mem=32MB
      -c max_connections=200
      -c random_page_cost=1.1
      -c effective_io_concurrency=200

  redis-prod:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    command: |
      redis-server
      --maxmemory 1800mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
EOF

    echo -e "${GREEN}✓ Created docker-compose.hardware.yml${NC}"
}

# Function to create performance tuning script
create_tuning_script() {
    echo -e "${YELLOW}Creating performance tuning script...${NC}"
    
    cat > "$DEAN_ROOT/tune_performance.sh" << 'EOF'
#!/bin/bash
# DEAN Performance Tuning Script
# Run this after system startup for optimal performance

set -e

echo "Applying DEAN performance tuning..."

# Network optimizations
sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_keepalive_time=60
sysctl -w net.ipv4.tcp_keepalive_intvl=10
sysctl -w net.ipv4.tcp_keepalive_probes=6
sysctl -w net.core.netdev_max_backlog=5000

# Memory optimizations
echo 10 > /proc/sys/vm/swappiness
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag

# CPU optimizations
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "performance" > "$cpu"
done

# GPU optimizations (if available)
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi -pm 1
    nvidia-smi -pl 320  # RTX 3080 power limit
fi

echo "Performance tuning complete!"
EOF

    chmod +x "$DEAN_ROOT/tune_performance.sh"
    echo -e "${GREEN}✓ Created tune_performance.sh${NC}"
}

# Main execution
echo "Starting hardware detection and optimization..."
echo ""

# Detect hardware
detect_cpu
echo ""
detect_memory
echo ""
detect_gpu
echo ""
detect_storage
echo ""

# Apply optimizations
apply_cpu_optimizations
echo ""
apply_memory_optimizations
echo ""
apply_gpu_optimizations
echo ""

# Create configuration files
create_docker_override
echo ""
create_tuning_script
echo ""

# Summary
echo -e "${BLUE}Optimization Summary${NC}"
echo "==================="
echo "CPU: $DETECTED_CPU ($CPU_CORES cores)"
echo "Memory: ${TOTAL_MEM_GB}GB ($MEMORY_PROFILE profile)"
echo "GPU: $DETECTED_GPU"
echo "Storage: $STORAGE_TYPE"
echo ""

# Recommendations
echo -e "${BLUE}Recommendations${NC}"
echo "==============="

if [ "$DETECTED_CPU" != "i7" ] || [ $CPU_CORES -lt 8 ]; then
    echo "- Upgrade to Intel i7 (8+ cores) for optimal performance"
fi

if [ "$MEMORY_PROFILE" != "high" ]; then
    echo "- Upgrade to 32GB RAM for best performance"
fi

if [ "$DETECTED_GPU" != "rtx3080" ]; then
    echo "- RTX 3080 GPU recommended for ML acceleration"
fi

if [ "$STORAGE_TYPE" != "nvme" ] && [ "$STORAGE_TYPE" != "ssd" ]; then
    echo "- Use NVMe SSD for best I/O performance"
fi

if [ "$EUID" -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Note: Run this script as root to apply all optimizations${NC}"
    echo "  sudo $0"
fi

echo ""
echo -e "${GREEN}Hardware optimization complete!${NC}"
echo ""
echo "To use the optimized configuration:"
echo "  docker-compose -f docker-compose.prod.yml -f docker-compose.hardware.yml up -d"
echo ""
echo "For runtime tuning (requires root):"
echo "  sudo ./tune_performance.sh"