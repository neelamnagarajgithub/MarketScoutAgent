#!/bin/bash
# Quick launcher for semantic search system

echo "🚀 Market Intelligence Semantic Search System"
echo "=============================================="

# Check if Python virtual environment exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Check for required environment variables
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Warning: GOOGLE_API_KEY not set"
    echo "Some features may be limited without Gemini API access"
fi

echo ""
echo "Available commands:"
echo "1. Interactive search:  ./run_semantic.sh interactive"
echo "2. Quick test:          ./run_semantic.sh test"
echo "3. Full test suite:     ./run_semantic.sh fulltest"
echo "4. Direct query:        ./run_semantic.sh query 'your query here'"
echo "5. Query + JSON save:   ./run_semantic.sh run 'your query here'"
echo "6. Test optimizer:      ./run_semantic.sh optimizer"
echo ""

case "$1" in
    "interactive")
        echo "🤖 Starting interactive mode..."
        python semantic_cli.py
        ;;
    "test")
        echo "⚡ Running quick tests..."
        python test_semantic_search.py quick
        ;;
    "fulltest")
        echo "🧪 Running full test suite..."
        python test_semantic_search.py full
        ;;
    "query")
        if [ -n "$2" ]; then
            echo "🔍 Executing query: $2"
            python semantic_cli.py "$2"
        else
            echo "❌ Please provide a query: ./run_semantic.sh query 'your search here'"
        fi
        ;;
    "run")
        if [ -n "$2" ]; then
            echo "🚀 Running query with JSON save: $2"
            python run_query.py "$2"
        else
            echo "❌ Please provide a query: ./run_semantic.sh run 'your search here'"
        fi
        ;;
    "optimizer")
        echo "🔧 Testing query optimizer integration..."
        python test_optimizer.py
        ;;
    *)
        echo "🤖 Starting interactive mode by default..."
        python semantic_cli.py
        ;;
esac