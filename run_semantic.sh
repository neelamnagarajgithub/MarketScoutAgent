#!/bin/bash
# Enhanced Semantic Search Script with API Key Validation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║          Enhanced Semantic Search Engine         ║"
    echo "║         Market Intelligence Platform v2.0        ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_requirements() {
    echo -e "${YELLOW}🔍 Checking requirements...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 not found${NC}"
        exit 1
    fi
    
    # Check virtual environment (optional warning)
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        echo -e "${YELLOW}⚠️  No virtual environment detected${NC}"
        echo "Recommendation: activate your virtual environment first"
    fi
    
    # Check if config.yaml exists
    if [[ ! -f "config.yaml" ]]; then
        echo -e "${RED}❌ config.yaml not found${NC}"
        echo "Please ensure config.yaml exists with your API keys"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Requirements check completed${NC}"
}

validate_apis() {
    echo -e "${YELLOW}🔐 Validating API keys...${NC}"
    
    # Run API validation
    python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from app.api_validator import APIKeyValidator
import yaml

async def validate():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        validator = APIKeyValidator(config)
        results = await validator.validate_all_keys()
        valid_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        print(f'API Validation: {valid_count}/{total_count} keys valid')
        return valid_count > 0
    except Exception as e:
        print(f'Validation failed: {e}')
        return False

result = asyncio.run(validate())
sys.exit(0 if result else 1)
"
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ API validation completed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some APIs may be invalid, but continuing...${NC}"
    fi
}

show_help() {
    echo "Enhanced Semantic Search Commands:"
    echo ""
    echo "  search 'query'     - Execute semantic search"
    echo "  interactive        - Start interactive mode"
    echo "  test              - Run API validation tests"
    echo "  validate          - Validate API keys"
    echo "  benchmark         - Performance benchmark"
    echo "  help              - Show this help"
    echo ""
    echo "Examples:"
    echo "  ./run_semantic.sh search 'OpenAI market analysis'"
    echo "  ./run_semantic.sh interactive"
    echo "  ./run_semantic.sh validate"
}

run_search() {
    local query="$1"
    if [[ -z "$query" ]]; then
        echo -e "${RED}❌ Please provide a search query${NC}"
        echo "Usage: $0 search 'your query here'"
        exit 1
    fi
    
    echo -e "${BLUE}🔍 Executing search: $query${NC}"
    echo "=" * 70
    
    python3 semantic_cli.py "$query"
}

run_interactive() {
    echo -e "${BLUE}🤖 Starting interactive mode...${NC}"
    python3 semantic_cli.py --interactive
}

run_benchmark() {
    echo -e "${BLUE}📊 Running performance benchmark...${NC}"
    
    queries=(
        "NVIDIA AI strategy analysis" 
        "AI startup funding trends 2024"
        "OpenAI competitive landscape"
    )
    
    for query in "${queries[@]}"; do
        echo -e "${YELLOW}Testing: $query${NC}"
        start_time=$(date +%s.%N)
        python3 semantic_cli.py "$query" --format summary > /dev/null
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc)
        echo -e "${GREEN}✅ Completed in ${duration}s${NC}"
    done
}

main() {
    print_header
    check_requirements
    validate_apis
    
    case "${1:-help}" in
        "search"|"query")
            run_search "$2"
            ;;
        "interactive"|"i")
            run_interactive
            ;;
        "test"|"validate")
            echo -e "${BLUE}🧪 Running API validation tests...${NC}"
            python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from app.api_validator import APIKeyValidator
import yaml

async def test_apis():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    validator = APIKeyValidator(config)
    results = await validator.validate_all_keys()
    for service, valid in results.items():
        status = '✅' if valid else '❌'
        print(f'{status} {service}: {"Valid" if valid else "Invalid"}')

asyncio.run(test_apis())
"
            ;;
        "benchmark"|"bench")
            run_benchmark
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"