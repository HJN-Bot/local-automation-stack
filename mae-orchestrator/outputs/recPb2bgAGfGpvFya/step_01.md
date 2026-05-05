**Codex CLI: Core Design Principles**

1.  **Terminal-Native Interaction:**
    *   **Principle:** The interface is the command line itself. The tool is designed to behave like a native shell extension where users interact with AI via standard flags and arguments (e.g., `gpt "commit this"`).
    *   **Mechanism:** It acts as a bridge between natural language input and shell output, focusing on single-turn or short-conversation exchanges to execute immediate tasks.

2.  **Direct Execution Model (The "Doer"):**
    *   **Principle:** The primary function is to translate intent into executable shell commands quickly.
    *   **Mechanism:** It prioritizes generating valid shell syntax over maintaining long-term state. The "Agent" loop is tight: Input -> Generate Command -> (User Confirm) -> Execute -> Output Result.

3.  **Simplicity and Composability:**
    *   **Principle:** Lean architecture that integrates easily into existing Unix pipelines.
    *   **Mechanism:** It relies less on complex internal file management or state retention and more on passing data to standard LLM APIs (primarily OpenAI) and piping results back to the user.

---

**Claude Code: Core Design Principles**

1.  **Project-Centric Agentic Architecture:**
    *   **Principle:** The agent operates with a holistic understanding of the entire codebase, not just the current file or terminal line.
    *   **Mechanism:** It builds a semantic map of the project structure, allowing it to navigate, edit, and reason across multiple files and modules simultaneously.

2.  **Autonomous Orchestration (The "Planner"):**
    *   **Principle:** The tool is designed to handle complex, multi-step tasks with minimal hand-holding.
    *   **Mechanism:** It employs a "Think-Act-Observe" loop where Claude autonomously decides to read files, run tests, analyze error logs, and apply diffs, looping until the task is complete or it encounters a critical blocker.

3.  **Rich State Management and Diffing:**
    *   **Principle:** Maintain a persistent context of the project state to ensure safe and reversible modifications.
    *   **Mechanism:** Unlike simple command generators, it manages a workspace of changes, presents unified diffs, and allows for granular approval of specific edits before applying them.

4.  **Deep Model Integration:**
    *   **Principle:** Leveraging specific native capabilities of the Claude 3.5 Sonnet model (e.g., extended context window, tool use).
    *   **Mechanism:** The architecture is optimized for Claude's specific strengths in coding and logical reasoning, treating the LLM not just as a text generator but as a reasoning engine controlling the CLI.