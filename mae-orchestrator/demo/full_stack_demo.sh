#!/bin/bash
# ──────────────────────────────────────────────────────────────
# MAE Full-Stack Demo — GitHub + OpenClaw + Codex + Claude
# ──────────────────────────────────────────────────────────────
# 一键跑通全链路，验证三层框架的所有集成点。
#
# 用法：
#   bash demo/full_stack_demo.sh          # 全链路（需 CLI 可用）
#   bash demo/full_stack_demo.sh dry      # Dry-run 模式（只显示决策）
#   bash demo/full_stack_demo.sh gh       # GitHub 集成测试
#
# 前置条件：
#   - MAE Orchestrator 已部署
#   - codex CLI 已认证（codex --version）
#   - claude CLI 已认证（claude --version）
#   - gh CLI 已认证（gh auth status）
# ──────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

MODE="${1:-full}"
VENV_PYTHON="venv/bin/python3"
MAE_SUBMIT="/Users/jianan/.openclaw/workspace/tools/mae_submit.py"

# ── Banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║       MAE Full-Stack Demo — L1+L2+L3 Integration        ║${NC}"
echo -e "${BOLD}${CYAN}║       OpenClaw → MAE Router → Codex/Claude CLI          ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Health Check ─────────────────────────────────────────────
echo -e "${BOLD}🔍 环境检查${NC}"
echo "──────────────────────────────────────────────────"

check_ok() { echo -e "  ${GREEN}✅${NC} $1"; }
check_warn() { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
check_fail() { echo -e "  ${RED}❌${NC} $1"; }

# Codex
if codex --version &>/dev/null; then
    V=$(codex --version 2>&1 | head -1)
    check_ok "Codex CLI: $V"
else
    check_fail "Codex CLI 不可用"
fi

# Claude
if claude --version &>/dev/null; then
    V=$(claude --version 2>&1 | head -1)
    check_ok "Claude CLI: $V"
else
    check_fail "Claude CLI 不可用"
fi

# GitHub
if gh auth status &>/dev/null; then
    check_ok "GitHub CLI: 已认证"
else
    check_warn "GitHub CLI: 未认证（跳过 GitHub 集成）"
fi

# MAE
if [ -f "$VENV_PYTHON" ]; then
    check_ok "MAE venv: 就绪"
else
    check_fail "MAE venv: 不可用"
fi

# Rate limit check (quick)
echo ""
echo -e "${BOLD}🔍 CLI 用量状态${NC}"
echo "──────────────────────────────────────────────────"

CODEX_LIMIT=$(codex exec "ok" 2>&1 | grep -i "limit\|reset" || true)
CLAUDE_LIMIT=$(claude -p "ok" --max-turns 1 2>&1 | grep -i "limit\|reset" || true)

if echo "$CODEX_LIMIT" | grep -qi "limit"; then
    echo -e "  ${YELLOW}Codex:${NC} $CODEX_LIMIT"
else
    echo -e "  ${GREEN}Codex:${NC} 可用"
fi

if echo "$CLAUDE_LIMIT" | grep -qi "limit"; then
    echo -e "  ${YELLOW}Claude:${NC} $CLAUDE_LIMIT"
else
    echo -e "  ${GREEN}Claude:${NC} 可用"
fi

echo ""

# ── Test 1: Router Decision Display ──────────────────────────
echo -e "${BOLD}${BLUE}📋 Test 1: 路由决策展示${NC}"
echo "──────────────────────────────────────────────────"
echo "展示三个不同类型的任务，MAE Router 如何选择执行路径："
echo ""

declare -A TESTS
TESTS["research"]="分析 2026 年 AI Agent 框架的最新进展和趋势"
TESTS["code"]="修复 src/utils.py 中的类型错误，重构为 dataclass"
TESTS["refactor"]="审查并优化这段代码的性能瓶颈"

for TYPE in research code refactor; do
    CONTENT="${TESTS[$TYPE]}"
    echo -e "  ${CYAN}类型:${NC} $TYPE"
    echo -e "  ${CYAN}内容:${NC} ${CONTENT:0:60}..."
    
    if [ "$MODE" = "dry" ]; then
        $VENV_PYTHON "$MAE_SUBMIT" --type "$TYPE" --content "$CONTENT" --dry-run 2>&1 | head -3
    fi
    
    # Show routing decision from router.py
    $VENV_PYTHON -c "
from router import ROUTING_TABLE
cls, model, reason, fallback, escalation = ROUTING_TABLE.get('$TYPE')
print(f'  → Executor: {cls.__name__} | Model: {model}')
print(f'  → Reason:   {reason}')
print(f'  → Fallback: {fallback}')
print(f'  → Escalate: {escalation}')
" 2>&1
    echo ""
done

# ── Test 2: Dry-Run Pipeline (always works) ──────────────────
echo -e "${BOLD}${BLUE}📋 Test 2: Dry-Run 全链路追踪${NC}"
echo "──────────────────────────────────────────────────"
echo "模拟一次完整执行，展示每个步骤的路由决策："
echo ""

$VENV_PYTHON "$MAE_SUBMIT" \
    --type pipeline \
    --content "分析 Codex CLI 和 Claude Code 在 Agent 编排上的架构差异，给出选择建议" \
    --enable-cli \
    --dry-run \
    2>&1 || true

echo ""

# ── Test 3: Real Execution (if CLIs available) ───────────────
if [ "$MODE" != "dry" ]; then
    echo -e "${BOLD}${BLUE}📋 Test 3: 真实 CLI 执行${NC}"
    echo "──────────────────────────────────────────────────"
    
    if echo "$CODEX_LIMIT$CLAUDE_LIMIT" | grep -qi "limit"; then
        echo -e "  ${YELLOW}⚠️  CLI 当前被限流，跳过真实执行。${NC}"
        echo -e "  ${YELLOW}   限制解除后运行: bash demo/full_stack_demo.sh${NC}"
        echo ""
        echo -e "  ${CYAN}预计可用时间:${NC}"
        echo "$CODEX_LIMIT" | grep -o "May [0-9]*.*[AP]M" | while read t; do
            echo "    Codex: $t"
        done
        echo "$CLAUDE_LIMIT" | grep -o "[0-9]*:[0-9]*am" | while read t; do
            echo "    Claude: $t"
        done
    else
        echo -e "  ${GREEN}CLI 可用，执行真实任务…${NC}"
        echo ""
        
        # Task 3a: Code task via Unified CLI (auto-route to Codex)
        echo -e "  ${CYAN}3a. 代码任务 → UnifiedCLIExecutor (auto)${NC}"
        $VENV_PYTHON "$MAE_SUBMIT" \
            --type code \
            --content "在 /tmp/mae_demo/ 创建一个 Python CLI 工具 greetings.py，接受 --name 参数并打印问候语，包含类型注解和 argparse" \
            --cli auto \
            2>&1 | tail -5
        echo ""
        
        # Task 3b: Creative task via Unified CLI (auto-route to Claude)
        echo -e "  ${CYAN}3b. 设计任务 → UnifiedCLIExecutor (auto → Claude)${NC}"
        $VENV_PYTHON "$MAE_SUBMIT" \
            --type code \
            --content "设计一个 Agent 编排系统的架构图，用文字描述各层职责和通信协议" \
            --cli auto \
            2>&1 | tail -5
        echo ""
    fi
fi

# ── Test 4: GitHub Integration ───────────────────────────────
if [ "$MODE" = "gh" ] || [ "$MODE" = "full" ]; then
    echo -e "${BOLD}${BLUE}📋 Test 4: GitHub 集成${NC}"
    echo "──────────────────────────────────────────────────"
    
    if ! gh auth status &>/dev/null; then
        echo -e "  ${YELLOW}⚠️  GitHub CLI 未认证，跳过。${NC}"
        echo -e "  ${YELLOW}   登录: gh auth login${NC}"
    else
        # Find or create demo repo
        DEMO_REPO="jianan/mae-fullstack-demo"
        
        if gh repo view "$DEMO_REPO" &>/dev/null 2>&1; then
            echo -e "  ${GREEN}Demo repo:${NC} github.com/$DEMO_REPO (已存在)"
        else
            echo -e "  ${CYAN}创建 demo repo…${NC}"
            gh repo create "$DEMO_REPO" --public --description "MAE Full-Stack Demo — OpenClaw + Codex + Claude" 2>&1 || true
        fi
        
        # Clone if not already
        DEMO_DIR="/tmp/mae_demo_repo"
        if [ ! -d "$DEMO_DIR" ]; then
            git clone "https://github.com/$DEMO_REPO" "$DEMO_DIR" 2>&1 || true
        fi
        
        echo ""
        echo -e "  ${GREEN}GitHub 集成流程:${NC}"
        echo "  ┌─────────────────────────────────────────┐"
        echo "  │ GitHub Issue                             │"
        echo "  │   ↓ gh issue view                        │"
        echo "  │ OpenClaw (L1) 接收并解析                  │"
        echo "  │   ↓ mae_submit.py --type code             │"
        echo "  │ MAE Router (L2) 路由决策                   │"
        echo "  │   ↓ UnifiedCLIExecutor --cli auto         │"
        echo "  │ Codex/Claude CLI (L3) 执行修改             │"
        echo "  │   ↓ gh issue comment + gh pr create       │"
        echo "  │ GitHub PR / Issue Comment                 │"
        echo "  └─────────────────────────────────────────┘"
        echo ""
        echo -e "  ${CYAN}触发命令:${NC}"
        echo "  \$ gh issue view <number> --json title,body | \\"
        echo "    $VENV_PYTHON $MAE_SUBMIT --type code --cli auto --content \"\$(cat)\""
        echo ""
    fi
fi

# ── Summary ──────────────────────────────────────────────────
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                    Demo Complete                         ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}新增文件:${NC}"
echo "  executors/unified_cli.py   — 统一 CLI 执行器 (Codex+Claude auto 路由)"
echo "  tools/search.py            — GLM web_search 封装"
echo "  demo/full_stack_demo.sh    — 本文件"
echo ""
echo -e "${BOLD}修改文件:${NC}"
echo "  executors/pipeline.py      — 加搜索注入 + CLI升级 + 递归 + 质量门控"
echo "  router.py                  — research→Pipeline, code→UnifiedCLI"
echo "  tools/mae_submit.py        — 加 --dry-run, --enable-cli, --cli auto"
echo ""
echo -e "${BOLD}可用的执行路径:${NC}"
echo ""
echo "  # Research（自动搜索）"
echo "  python3 $MAE_SUBMIT --type research --content \"分析XX趋势\""
echo ""
echo "  # Code（auto 路由 Codex/Claude）"
echo "  python3 $MAE_SUBMIT --type code --cli auto --content \"修复XX bug\""
echo ""
echo "  # Pipeline（步骤级搜索+CLI升级）"
echo "  python3 $MAE_SUBMIT --type pipeline --enable-cli --content \"XX多步骤任务\""
echo ""
echo "  # Dry-run（只看决策不执行）"
echo "  python3 $MAE_SUBMIT --type code --cli auto --dry-run --content \"XX\""
echo ""
echo -e "${BOLD}下一步:${NC}"
echo "  等 Codex/Claude 限制解除后，运行:"
echo -e "  ${CYAN}bash demo/full_stack_demo.sh${NC}"
echo ""
