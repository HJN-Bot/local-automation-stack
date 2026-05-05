**Codex CLI: Agent Orchestration Architecture Deconstruction**

**1. Tool Invocation: The Shell as the Primitive Interface**
*   **Mechanism:** Codex CLI does not rely on a complex internal library of function calls (e.g., `read_file`, `search_symbol`). Instead, it utilizes the LLM's text generation capabilities to produce raw shell commands (bash, zsh, powershell) as the primary output.
*   **Abstraction Level:** The "Tool" is the command-line interface itself. The agent orchestrates actions by generating syntactically correct strings that the native shell parses. This bypasses the need for the CLI to implement specific file I/O logic, delegating all system interactions to the standard operating system shell.
*   **Constraint:** It relies heavily on prompt engineering to constrain the LLM to output *only* executable code within specific delimiters, separating the reasoning from the executable artifact.

**2. Loop Mechanisms: Linear, User-Dependent Execution**
*   **Architecture Type:** Open-Loop / Single-Turn Orchestration.
*   **Flow:**
    1.  **Input:** User provides a natural language request (e.g., "resize all images").
    2.  **Generation:** The LLM generates a single command or pipeline string.
    3.  **Gate (The "Confirm" Step):** Execution is paused for user validation. The system does not auto-execute.
    4.  **Execution:** The shell runs the command.
    5.  **Output:** The result is displayed to the user.
*   **Loop Characteristics:** The loop effectively terminates after execution. The LLM does not automatically observe the output to generate a follow-up command. If an error occurs, the user must explicitly feed the error back into the prompt to initiate a new loop cycle. The "Agent" lacks the autonomy to self-correct or chain commands without user intervention.

**3. Environment Interaction: Context-Limited and Stateless**
*   **Context Awareness:** The interaction is restricted to the immediate prompt context. Codex CLI typically does not maintain a persistent semantic index of the project structure or a vector database of file contents.
*   **File System Access:** Access is **indirect**. The agent cannot "see" files; it can only suggest commands that *read* files (e.g., `cat main.py`, `grep -r "function"`). The user acts as the sensor, executing these commands and relaying information back to the LLM if necessary.
*   **State Management:** The architecture is stateless. Each request is independent, treating the environment as a black box. It does not track file changes, git states, or test results internally. It treats the terminal environment as ephemeral, focusing solely on translating the current intent into a valid shell command.